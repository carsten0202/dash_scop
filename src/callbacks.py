from dash import Input, Output, html, dcc
import plotly.express as px
import numpy as np
import io
import os
from data_loader import load_seurat_rds

# Load the Seurat data
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

# Store the last generated figure
last_figure = None  

def register_callbacks(app):

    @app.callback(
        Output("gene-selector", "options"),
        Output("cell-type-filter", "options"),
        Input("plot-selector", "value")
    )
    def update_gene_and_celltype_options(plot_type):
        gene_options = [{"label": gene, "value": gene} for gene in gene_matrix_df.index]
        cell_type_options = [{"label": cell, "value": cell} for cell in metadata_df["seurat_clusters"].unique()]
        return gene_options, cell_type_options

    @app.callback(
        Output("plot-container", "children"),
        Input("plot-selector", "value"),
        Input("gene-selector", "value"),
        Input("cell-type-filter", "value"),
        prevent_initial_call=True
    )
    def update_plots(plot_type, selected_genes, selected_cell_types):
        global last_figure  # Store last figure for export

        if selected_genes is None or len(selected_genes) == 0:
            selected_genes = gene_matrix_df.index[:1]
        if selected_cell_types is None or len(selected_cell_types) == 0:
            selected_cell_types = metadata_df["seurat_clusters"].unique()

        filtered_metadata = metadata_df[metadata_df["seurat_clusters"].isin(selected_cell_types)]
        filtered_cells = filtered_metadata.index
        filtered_expression = gene_matrix_df.loc[selected_genes, filtered_cells]

        plot_figures = []

        if plot_type == "boxplot":
            df_melted = filtered_expression.melt(var_name="Cell", value_name="Expression")
            df_melted["CellType"] = metadata_df.loc[df_melted["Cell"], "cell_type"]
            df_melted["Gene"] = np.tile(selected_genes, len(df_melted) // len(selected_genes))

            for gene in selected_genes:
                last_figure = px.box(
                    df_melted[df_melted["Gene"] == gene],
                    x="CellType",
                    y="Expression",
                    title=f"Boxplot for {gene}"
                )
                plot_figures.append(html.Div(dcc.Graph(figure=last_figure), style={"width": "48%", "display": "inline-block"}))

        elif plot_type == "umap":
            last_figure = px.scatter(
                umap_df.loc[filtered_cells],
                x="UMAP1",
                y="UMAP2",
                color=metadata_df.loc[filtered_cells, "cell_type"],
                title="UMAP Scatterplot"
            )
            plot_figures.append(html.Div(dcc.Graph(figure=last_figure), style={"width": "100%"}))

        elif plot_type == "violin":
            df_melted = filtered_expression.melt(var_name="Cell", value_name="Expression")
            df_melted["CellType"] = metadata_df.loc[df_melted["Cell"], "cell_type"]
            df_melted["Gene"] = np.tile(selected_genes, len(df_melted) // len(selected_genes))

            last_figure = px.violin(
                df_melted,
                x="Gene",
                y="Expression",
                color="CellType",
                box=True,
                points="all",
                title="Violin Plot"
            )
            plot_figures.append(html.Div(dcc.Graph(figure=last_figure), style={"width": "100%"}))

        elif plot_type == "heatmap":
            heatmap_data = filtered_expression.to_numpy()
            last_figure = px.imshow(heatmap_data, color_continuous_scale="Viridis", title="Gene Expression Heatmap")
            plot_figures.append(html.Div(dcc.Graph(figure=last_figure), style={"width": "100%"}))

        return plot_figures

    @app.callback(
        Output("download-plot", "data"),
        Input("download-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def download_plot(n_clicks):
        """Saves the last generated plot as an SVG file and provides it for download."""
        global last_figure

        if last_figure is None:
            return None  # No figure to download

        # Save figure as SVG
        svg_buffer = io.StringIO()
        last_figure.write_image(svg_buffer, format="svg")

        # Encode SVG content as a downloadable file
        encoded_svg = svg_buffer.getvalue()
        return dcc.send_string(encoded_svg, filename="plot.svg")
