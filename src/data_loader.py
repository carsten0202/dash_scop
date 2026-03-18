import os

import pandas as pd
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter
from rpy2.robjects.packages import importr

# Load R packages
try:
    importr("base")
    importr("Seurat")
    importr("stats")
except Exception as e:
    raise ImportError("Required R packages not found. Please ensure 'Seurat' and 'stats' are installed in your R environment.") from e

# Define R functions for loading Seurat objects and extracting data
ro.r("""
    extract_data <- function(seurat_obj, assay, layer) {
        metadata <- seurat_obj@meta.data  # Cell metadata
        gene_matrix <- as.data.frame(LayerData(seurat_obj, assay = assay, layer = layer)) # Expression matrix
        umap <- as.data.frame(Embeddings(seurat_obj, reduction = "umap"))  # UMAP coordinates
        return(list(metadata = metadata, gene_matrix = gene_matrix, umap = umap))
    }

    .seurat_registry <- new.env(parent = emptyenv())

    register_seurat_matrix <- function(file_path, assay, layer) {
        obj <- LoadSeuratRds(file_path)

        mat <- LayerData(obj, assay = assay, layer = layer)
        metadata <- obj@meta.data
        umap <- as.data.frame(Embeddings(obj, reduction = "umap"))
        genes <- rownames(mat)
        barcodes <- colnames(mat)

        handle <- paste0(
            basename(file_path), "_",
            as.integer(Sys.time()), "_",
            sample.int(1e9, 1)
        )

        .seurat_registry[[handle]] <- list(
            mat = mat,
            metadata = metadata,
            umap = umap,
            genes = genes,
            barcodes = barcodes
        )

        rm(obj)
        invisible(gc())

        list(
            handle = handle,
            metadata = metadata,
            umap = umap,
            genes = genes,
            barcodes = colnames(mat)
        )
    }

    get_expression_subset_matrix <- function(handle, genes = NULL, cells = NULL) {
        entry <- .seurat_registry[[handle]]
        if (is.null(entry)) {
            stop("Unknown handle: ", handle)
        }

        mat <- entry$mat
        if (!is.null(genes)) {
            genes <- intersect(genes, rownames(mat))
            mat <- mat[genes, , drop = FALSE]
        }
        if (!is.null(cells)) {
            cells <- intersect(cells, colnames(mat))
            mat <- mat[, cells, drop = FALSE]
        }
     
        bytes_needed <- as.double(nrow(mat)) * as.double(ncol(mat)) * 8
        max_heatmap_bytes <- 2000 * 1024^2  # e.g. 2000 MB
        if (bytes_needed > max_heatmap_bytes) {
            stop(
                sprintf(
                    "Heatmap subset too large to materialize safely (%d x %d, ~%.1f MB dense). Refine filters or reduce genes/cells.",
                    nrow(mat), ncol(mat), bytes_needed / 1024^2
                )
            )
        }
     
        list(
            data = as.matrix(mat),
            genes = rownames(mat),
            cells = colnames(mat),
            nrow = nrow(mat),
            ncol = ncol(mat)
        )
    }

    remove_seurat_matrix <- function(handle) {
        if (exists(handle, envir = .seurat_registry, inherits = FALSE)) {
            rm(list = handle, envir = .seurat_registry)
            invisible(gc())
            return(TRUE)
        }
        FALSE
    }

"""
)




def _optimize_metadata_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        s = df[col]
        if pd.api.types.is_object_dtype(s):
            nunique = s.nunique(dropna=False)
            if nunique / max(len(s), 1) < 0.5:
                df[col] = s.astype("category")
        elif pd.api.types.is_integer_dtype(s):
            df[col] = pd.to_numeric(s, downcast="integer")
        elif pd.api.types.is_float_dtype(s):
            df[col] = pd.to_numeric(s, downcast="float")
    return df

def load_seurat_rds(file_path: str | os.PathLike[str], assay="SCT", layer="data"):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found.")

    with localconverter(ro.default_converter + pandas2ri.converter):
        extracted = ro.r["register_seurat_matrix"](str(file_path), assay, layer) # type: ignore

        handle = str(extracted[0][0])
        metadata_df = _optimize_metadata_dtypes(extracted[1])

        umap_df = extracted[2]
        umap_df.columns = umap_df.columns.str.upper()

        gene_names = list(extracted[3])

        mat = ro.r["get_expression_subset_matrix"](handle, extracted[3][1:7], extracted[4][1:7]) # type: ignore
        print(f"Loaded Seurat object from {file_path} with handle {handle}. Metadata shape: {metadata_df.shape}, UMAP shape: {umap_df.shape}, Number of genes: {len(gene_names)}")
        print(f'Data Bit: {extracted[4][1:7]}')
        print(f'Meta Matrix: {metadata_df}')
        print(f"Data Matrix: {mat[0]}\nMatrix Shape: {mat[0].shape}")

    return {
        "seurat_handle": handle,
        "gene_names": gene_names,
        "metadata": metadata_df,
        "umap": umap_df,
    }



def old_load_seurat_rds(file_path: str | os.PathLike[str], assay="SCT", layer="data"):
    """Reads an RDS file containing a Seurat object and extracts relevant data."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found.")

    with localconverter(ro.default_converter + pandas2ri.converter):
        """
        # Join layers to convert to SCE
        seurat_obj <- SeuratObject::JoinLayers(seurat_obj, assay = "RNA")
        sce_obj <- Seurat::as.SingleCellExperiment(seurat_obj)

        # Convert gene names to Symbols
        library(annotation)
        org_db <- org.Mm.eg.db

        ensembl_ids <- rownames(sce_obj)
        gene_symbols <- AnnotationDbi::mapIds(
            org_db,
            keys = ensembl_ids,
            column = "SYMBOL",
            keytype = "ENSEMBL"
        )

        rownames(sce_obj) <- ifelse(
            is.na(gene_symbols[rownames(sce_obj)]),
            ensembl_ids,
            gene_symbols[rownames(sce_obj)]
        )
        """

        seurat_obj = ro.r["LoadSeuratRds"](str(file_path))  # Load Seurat RDS file # type: ignore
        extracted = ro.r["extract_data"](seurat_obj, assay, layer)  # type: ignore

        # Prepare metadata DataFrame
        metadata_df = pd.concat(
            [
                extracted[0][
                    [x for x in extracted[0].columns if extracted[0][x].dtype in ["object", "category", "str"]]
                ].astype(
                    "category"
                ),  # Extract columns from metadata as pandas DataFrame that are of type 'object', 'category' or 'str'
                extracted[0][
                    [x for x in extracted[0].columns if extracted[0][x].dtype not in ["object", "category", "str"]]
                ],  # Extract non-categorical (probably numeric) columns from metadata
            ],
            axis=1,
        )

        # DataFrame suitable for boxplots & violon plots
        gene_matrix_df = extracted[1]  # Gene expression matrix as pandas DataFrame
#        boxplot_df = pd.concat([metadata_df, gene_matrix_df.transpose()], axis=1)

        # DataFrame for Heatmaps
#        heatmap_df = gene_matrix_df.apply(zscore, axis=1, result_type="broadcast")

        # DataFrame for UMAP plotting
        umap_df = extracted[2]  # UMAP data as pandas DataFrame...
        umap_df.columns = umap_df.columns.str.upper()  # ...and set column names to uppercase

        return {
            "boxplot": None,
            "gene_counts": gene_matrix_df,
            "heatmap": None,
            "metadata": metadata_df,
            "umap": umap_df,
        }
