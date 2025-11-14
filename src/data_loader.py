import os

import rpy2.robjects as ro
import rpy2.robjects.packages as rpackages
import rpy2.robjects.pandas2ri as pd2ri
from rpy2.robjects import default_converter
from rpy2.robjects.conversion import localconverter

# Load R packages
seurat = rpackages.importr("Seurat")


def load_seurat_rds(file_path: str | os.PathLike[str], assay="SCT", layer="data"):
    """Reads an RDS file containing a Seurat object and extracts relevant data."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found.")

    with localconverter(default_converter + pd2ri.converter):
        ro.r("""
        extract_data <- function(seurat_obj, assay, layer) {
            metadata <- seurat_obj@meta.data  # Cell metadata
            gene_matrix <- as.data.frame(LayerData(seurat_obj, assay = assay, layer = layer)) # Expression matrix
            umap <- as.data.frame(Embeddings(seurat_obj, reduction = "umap"))  # UMAP coordinates
            return(list(metadata = metadata, gene_matrix = gene_matrix, umap = umap))
        }
        """)
        seurat_obj = ro.r["LoadSeuratRds"](str(file_path))  # Load Seurat RDS file # type: ignore
        extracted = ro.r["extract_data"](seurat_obj, assay, layer)  # type: ignore
        metadata_df = extracted["metadata"][
            [x for x in extracted["metadata"].columns if extracted["metadata"][x].dtype in ["object", "category"]]
        ]  # Extract columns from metadata as pandas DataFrame that are of type 'object' or 'categorical'
        gene_matrix_df = extracted["gene_matrix"]  # Gene expression matrix as pandas DataFrame
        umap_df = extracted["umap"]  # UMAP data as pandas DataFrame...
        umap_df.columns = umap_df.columns.str.upper()  # ...and set column names to uppercase

        print(f"{metadata_df}")

        return metadata_df, gene_matrix_df, umap_df
