import os

from dash import Dash

from callbacks import register_callbacks
from data_loader import load_seurat_rds
from layout import layout

# Initialize Dash app
app = Dash(__name__)
app.layout = layout

# Register callbacks
register_callbacks(app)


def main():
    ip = os.getenv("DASH_IP", "127.0.0.1")
    port = int(os.getenv("DASH_PORT", 8050))
    debug = os.getenv("DASH_DEBUG", "True") == "True"

    # Path to the test RDS file
    RDS_FILE = "testdata/20220818_brain_10x-test_rna-seurat.rds"
    if not os.path.exists(RDS_FILE):
        raise FileNotFoundError(f"Missing test data: {RDS_FILE}")
    metadata_df, gene_matrix_df, umap_df = load_seurat_rds(RDS_FILE)

    # Print some info for verification
    print("Metadata Sample:")
    print(metadata_df.head())
    print("\nGene Expression Matrix Sample:")
    print(gene_matrix_df.iloc[:5, :5])
    print("\nUMAP Sample:")
    print(umap_df.head())

    app.run_server(host=ip, port=port, debug=debug)


if __name__ == "__main__":
    main()
