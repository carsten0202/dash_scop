import os

import rpy2.robjects as ro
import rpy2.robjects.numpy2ri
import rpy2.robjects.packages as rpackages
import rpy2.robjects.pandas2ri

# Activate automatic conversion between R and Python
rpy2.robjects.numpy2ri.activate()
rpy2.robjects.pandas2ri.activate()

# Load R packages
base = rpackages.importr("base")
seurat = rpackages.importr("Seurat")


def load_seurat_rds(file_path, data="data"):
    """Reads an RDS file containing a Seurat object and extracts relevant data."""

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found.")

    ro.r("""
    load_seurat <- function(file_path) {
        library(Seurat)
        obj <- LoadSeuratRds(file_path)  # Load Seurat object
        return(obj)
    }
    """)

    seurat_obj = ro.r["load_seurat"](file_path)  # type: ignore

    # Extract metadata and expression data
    ro.r("""
    extract_data <- function(seurat_obj, assay, layer) {
        metadata <- seurat_obj@meta.data  # Cell metadata
        gene_matrix <- as.data.frame(LayerData(seurat_obj, assay = assay, layer = layer)) # Expression matrix
        umap <- as.data.frame(Embeddings(seurat_obj, reduction = "umap"))  # UMAP coordinates
        list(metadata = metadata, gene_matrix = gene_matrix, umap = umap)
    }
    """)

    extracted = ro.r["extract_data"](seurat_obj, "SCT", data)  # type: ignore

    metadata_df = rpy2.robjects.pandas2ri.rpy2py(extracted[0])  # Convert to Pandas DataFrame
    gene_matrix_df = rpy2.robjects.pandas2ri.rpy2py(extracted[1])  # Gene expression matrix
    umap_df = rpy2.robjects.pandas2ri.rpy2py(extracted[2])  # UMAP data
    umap_df.columns = umap_df.columns.str.upper()

    return metadata_df, gene_matrix_df, umap_df
