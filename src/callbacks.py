import io
import os

import numpy as np
import plotly.express as px
from dash import Input, Output, dcc, html

from data_loader import load_seurat_rds

# Load the Seurat data
RDS_FILE = os.getenv("DASH_RDS_FILE", "testdata/seurat_obj_downsampled.rds")
metadata_df, gene_matrix_df, umap_df = load_seurat_rds(RDS_FILE)

# Some standard settings
max_features = 60

# Store the last generated figure
last_figure = None


def register_callbacks(app):
    from flask_caching import Cache

    # Initialize Flask-Caching **after** app creation
    cache = Cache(config={"CACHE_TYPE": "simple"})
    cache.init_app(app.server)

    @cache.memoize()
    def get_filtered_data(selected_genes, selected_cell_types):
        """Cache filtered expression data to avoid recomputation."""
        filtered_cells = metadata_df.index[metadata_df["seurat_clusters"].isin(selected_cell_types)]
        return gene_matrix_df.loc[selected_genes, filtered_cells]

    @app.callback(
        Output("gene-selector", "options"),
        Output("cell-type-filter", "options"),
        Input("plot-selector", "value"),
    )
    def update_gene_and_celltype_options(plot_type):
        gene_options = [{"label": gene, "value": gene} for gene in gene_matrix_df.index]
        cell_type_options = [{"label": cell, "value": cell} for cell in metadata_df["seurat_clusters"].unique()]
        return gene_options, cell_type_options

    @app.callback(
        Output("gene-selector-container", "style"),
        Input("plot-selector", "value"),
    )
    def toggle_gene_selector(plot_type):
        # List of plots that should show the gene selector
        plots_showing_genes = ["boxplot", "violin", "heatmap"]  # Update as needed
        if plot_type in plots_showing_genes:
            return {"display": "block"}  # Show
        else:
            return {"display": "none"}  # Hide

    @app.callback(
        Output("plot-container", "children"),
        Output("error-message", "children"),
        Input("plot-selector", "value"),
        Input("gene-selector", "value"),
        Input("cell-type-filter", "value"),
        prevent_initial_call=False,
    )
    def update_plots(plot_type, selected_genes, selected_cell_types):
        global last_figure  # Store last figure for export

        if selected_genes is None or len(selected_genes) == 0:
            selected_genes = gene_matrix_df.index
        if selected_cell_types is None or len(selected_cell_types) == 0:
            selected_cell_types = metadata_df["seurat_clusters"].unique()

        filtered_cells = metadata_df.index[metadata_df["seurat_clusters"].isin(selected_cell_types)]
        filtered_expression = get_filtered_data(selected_genes, selected_cell_types)

        plot_figures = []

        try:
            if plot_type == "boxplot" and len(selected_genes) <= max_features:
                df_melted = filtered_expression.melt(var_name="Cell", value_name="Expression")
                df_melted["CellType"] = df_melted["Cell"].map(metadata_df["seurat_clusters"])
                df_melted["Gene"] = np.tile(selected_genes, len(df_melted) // len(selected_genes))

                if len(selected_genes) <= max_features:
                    for gene in selected_genes:
                        last_figure = px.box(
                            df_melted[df_melted["Gene"] == gene],
                            x="CellType",
                            y="Expression",
                            title=f"Boxplot for {gene}",
                        )
                        plot_figures.append(
                            html.Div(dcc.Graph(figure=last_figure), style={"width": "48%", "display": "inline-block"})
                        )

            elif plot_type == "umap":
                last_figure = px.scatter(
                    umap_df.loc[filtered_cells],
                    x="UMAP_1",
                    y="UMAP_2",
                    color=metadata_df.loc[filtered_cells, "seurat_clusters"],
                    title="UMAP Scatterplot",
                )
                plot_figures.append(html.Div(dcc.Graph(figure=last_figure), style={"width": "100%"}))

            elif plot_type == "violin" and len(selected_genes) <= max_features:
                df_melted = filtered_expression.melt(var_name="Cell", value_name="Expression")
                df_melted["CellType"] = df_melted["Cell"].map(metadata_df["seurat_clusters"])
                df_melted["Gene"] = np.tile(selected_genes, len(df_melted) // len(selected_genes))
                last_figure = px.violin(
                    df_melted, x="Gene", y="Expression", color="CellType", box=True, points="all", title="Violin Plot"
                )
                if len(selected_genes) <= 50:
                    plot_figures.append(html.Div(dcc.Graph(figure=last_figure), style={"width": "100%"}))

            elif plot_type == "heatmap":
                heatmap_data = filtered_expression.to_numpy()
                last_figure = px.imshow(
                    heatmap_data,
                    color_continuous_scale="Viridis",
                    title="Gene Expression Heatmap",
                    x=filtered_expression.columns,  # columns
                    y=selected_genes,  # rows
                    aspect="auto",
                    # aspect="equal",
                    labels=dict(x="Cells", y="Genes", color="Expr"),  # axis titles & color-bar
                )

                # Don't show labels if there's too many
                if len(selected_genes) > max_features:
                    last_figure.update_yaxes(showticklabels=False)
                if len(filtered_expression.columns) > 2 * max_features:
                    last_figure.update_xaxes(showticklabels=False)

                plot_figures.append(
                    html.Div(dcc.Graph(figure=last_figure, style={"height": "70vh"}), style={"width": "100%"})
                )

            else:
                if selected_genes == gene_matrix_df.index:
                    raise ValueError("Please select one or more features.")
                elif len(selected_genes) > max_features:
                    raise ValueError(f"Please select no more than {max_features} features.")
                else:
                    raise ValueError("Something went wrong?")

        except ValueError as e:
            plot_figures.append(html.Div(id="error-message", style={"color": "red"}))
            return plot_figures, f"Error: {str(e)}"

        return plot_figures, ""

    @app.callback(
        Output("download-plot", "data"),
        Input("download-btn", "n_clicks"),
        prevent_initial_call=True,
    )
    def download_plot(n_clicks):
        """Saves the last generated plot as an SVG file and provides it for download."""
        global last_figure

        if last_figure is None:
            return None  # No figure to download

        # Save figure as SVG
        svg_buffer = io.BytesIO()
        last_figure.write_image(svg_buffer, format="svg")

        # Encode SVG content as a downloadable file
        encoded_svg = svg_buffer.getvalue()
        return dcc.send_bytes(encoded_svg, filename="plot.svg")
