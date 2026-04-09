import os
from collections import Counter, defaultdict

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
    .seurat_registry <- new.env(parent = emptyenv())

    infer_ensembl_species <- function(genes) {
        if (length(genes) == 0) {
            return(NA_character_)
        }

        normalized <- sub("\\\\..*$", "", genes)
        if (any(startsWith(normalized, "ENSMUS"), na.rm = TRUE)) {
            return("mouse")
        }
        if (any(startsWith(normalized, "ENSRN"), na.rm = TRUE)) {
            return("rat")
        }
        if (any(startsWith(normalized, "ENSG"), na.rm = TRUE)) {
            return("human")
        }

        NA_character_
    }

    map_ensembl_to_symbols <- function(genes) {
        if (length(genes) == 0) {
            return(rep(NA_character_, 0))
        }

        species <- infer_ensembl_species(genes)
        if (is.na(species) || !requireNamespace("AnnotationDbi", quietly = TRUE)) {
            return(rep(NA_character_, length(genes)))
        }

        org_pkg <- switch(
            species,
            human = "org.Hs.eg.db",
            mouse = "org.Mm.eg.db",
            rat = "org.Rn.eg.db",
            NA_character_
        )
        if (is.na(org_pkg) || !requireNamespace(org_pkg, quietly = TRUE)) {
            return(rep(NA_character_, length(genes)))
        }

        normalized <- sub("\\\\..*$", "", genes)
        org_db <- getExportedValue(org_pkg, org_pkg)
        mapped <- AnnotationDbi::mapIds(
            org_db,
            keys = unique(normalized),
            column = "SYMBOL",
            keytype = "ENSEMBL",
            multiVals = "first"
        )

        unname(mapped[normalized])
    }

    register_seurat_matrix <- function(file_path, assay, layer) {
        obj <- LoadSeuratRds(file_path)

        mat <- LayerData(obj, assay = assay, layer = layer)
        metadata <- obj@meta.data
        umap <- as.data.frame(Embeddings(obj, reduction = "umap"))
        genes <- rownames(mat)
        gene_symbols <- map_ensembl_to_symbols(genes)
        cells <- colnames(mat)

        handle <- paste0(
            basename(file_path), "_",
            as.integer(Sys.time()), "_",
            sample.int(1e9, 1)
        )

        .seurat_registry[[handle]] <- list(
            matrix = mat,
            metadata = metadata,
            umap = umap,
            genes = genes,
            cells = cells
        )

        rm(obj)
 
        list(
            handle = handle,
            metadata = metadata,
            umap = umap,
            genes = genes,
            gene_symbols = gene_symbols,
            cells = colnames(mat)
        )
    }

    get_expression_subset_matrix <- function(handle, genes = NULL, cells = NULL) {
        entry <- .seurat_registry[[handle]]
        if (is.null(entry)) {
            stop("Unknown handle: ", handle)
        }

        mat <- entry$matrix
        if (!is.null(genes)) {
            genes <- intersect(genes, rownames(mat))
            mat <- mat[genes, , drop = FALSE]
        }
        if (!is.null(cells)) {
            cells <- intersect(cells, colnames(mat))
            mat <- mat[, cells, drop = FALSE]
        }
     
        bytes_needed <- as.double(nrow(mat)) * as.double(ncol(mat)) * 8
        max_heatmap_bytes <- 5000 * 1024^2  # e.g. 5000 MB
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


def _build_gene_display_data(genes: list[str], gene_symbols: list[str]) -> tuple[dict[str, str], dict[str, str], dict[str, list[str]], dict[str, list[str]]]:
    resolved_symbols = []
    symbol_counts: Counter[str] = Counter()

    for gene, raw_symbol in zip(genes, gene_symbols, strict=False):
        symbol = raw_symbol.strip() if isinstance(raw_symbol, str) else ""
        if not symbol:
            symbol = gene
        resolved_symbols.append(symbol)
        if symbol != gene:
            symbol_counts[symbol] += 1

    gene_symbols_by_id = {}
    gene_labels = {}
    gene_ids_by_symbol: dict[str, list[str]] = defaultdict(list)
    gene_ids_by_symbol_folded: dict[str, list[str]] = defaultdict(list)

    for gene, symbol in zip(genes, resolved_symbols, strict=False):
        gene_symbols_by_id[gene] = symbol
        gene_labels[gene] = symbol if symbol == gene or symbol_counts[symbol] == 1 else f"{symbol} ({gene})"
        gene_ids_by_symbol[symbol].append(gene)
        gene_ids_by_symbol_folded[symbol.casefold()].append(gene)

    return gene_symbols_by_id, gene_labels, dict(gene_ids_by_symbol), dict(gene_ids_by_symbol_folded)

def load_seurat_rds(file_path: str | os.PathLike[str], assay="SCT", layer="data"):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found.")

    with localconverter(ro.default_converter + pandas2ri.converter):
        registry = ro.r["register_seurat_matrix"](str(file_path), assay, layer) # type: ignore

        handle = str(registry.getbyname("handle")[0])
        metadata_df = _optimize_metadata_dtypes(registry.getbyname("metadata"))
        umap_df = registry.getbyname("umap")
        umap_df.columns = umap_df.columns.str.upper()
        genes = list(registry.getbyname("genes"))
        gene_symbols = list(registry.getbyname("gene_symbols"))
        cells = list(registry.getbyname("cells"))

    gene_symbols_by_id, gene_labels, gene_ids_by_symbol, gene_ids_by_symbol_folded = _build_gene_display_data(
        genes,
        gene_symbols,
    )

    print(f"Loaded Seurat object from {file_path} with handle {handle}. Metadata shape: {metadata_df.shape}, UMAP shape: {umap_df.shape}")

    return {
        "seurat_handle": handle,
        "genes": genes,
        "gene_symbols": gene_symbols_by_id,
        "gene_labels": gene_labels,
        "gene_ids_by_symbol": gene_ids_by_symbol,
        "gene_ids_by_symbol_folded": gene_ids_by_symbol_folded,
        "cells": cells,
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
