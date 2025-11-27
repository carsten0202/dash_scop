import os

import pandas as pd
import rpy2.robjects as ro
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter
from rpy2.robjects.packages import importr

# Load R packages
base = importr("base")
seurat = importr("Seurat")
stats = importr("stats")


def load_seurat_rds(file_path: str | os.PathLike[str], assay="SCT", layer="data"):
    """Reads an RDS file containing a Seurat object and extracts relevant data."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found.")

    with localconverter(ro.default_converter + pandas2ri.converter):
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
        metadata_df = extracted[0][
            [x for x in extracted[0].columns if extracted[0][x].dtype in ["object", "category"]]
        ].astype(
            "category"
        )  # Extract columns from metadata as pandas DataFrame that are of type 'object' or 'category'
        gene_matrix_df = extracted[1]  # Gene expression matrix as pandas DataFrame
        umap_df = extracted[2]  # UMAP data as pandas DataFrame...
        umap_df.columns = umap_df.columns.str.upper()  # ...and set column names to uppercase

        # DataFrame suitable for boxplots
        combined_df = pd.DataFrame(
            {"Combined": [1] * len(metadata_df.index)}, dtype="category", index=metadata_df.index
        )
        boxplot_df = pd.concat([metadata_df, combined_df, gene_matrix_df.transpose()], axis=1)
        print(boxplot_df)
        print(boxplot_df.dtypes)

        return {"boxplot": boxplot_df, "gene_counts": gene_matrix_df, "metadata": metadata_df, "umap": umap_df}
