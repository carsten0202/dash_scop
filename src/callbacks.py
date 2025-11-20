import io
import os
import time
import uuid
from pathlib import Path

import dash_bootstrap_components as dbc
import numpy as np
import plotly.express as px
from dash import Input, Output, State, dcc, html, no_update
from flask_caching import Cache

import settings
from data_loader import load_seurat_rds

# Load the Seurat data
RDS_FILE = os.getenv("DASH_RDS_FILE", "testdata/seurat_obj_downsampled.rds")

# Code to be deleted. No reason to preload a dataset if the user selects one
data_dfs = load_seurat_rds(RDS_FILE, "SCT", "data")
gene_matrix_df = data_dfs["gene_counts"]
metadata_df = data_dfs["metadata"]


# Store the last generated figure
last_figure = None


def register_callbacks(app):
    # Initialize Flask-Caching **after** app creation
    cache = Cache(config={"CACHE_TYPE": "simple"})
    cache.init_app(app.server)

    @cache.memoize()
    def get_filtered_data(selected_genes, selected_cell_types):
        """Cache filtered expression data to avoid recomputation."""
        filtered_cells = metadata_df.index[metadata_df["seurat_clusters"].isin(selected_cell_types)]
        return gene_matrix_df.loc[selected_genes, filtered_cells]

    @app.callback(
        Output("file-list", "data"),
        Input("rescan", "n_clicks"),
        Input("init", "n_intervals"),
        prevent_initial_call=True,
    )
    def refresh_file_list(_clicks, _init):
        files = scan_files()
        # include simple metadata (mtime, size) if you like
        enriched = []
        for rel in files:
            p = (settings.BASE_DIR / rel).resolve()
            st = p.stat()
            enriched.append(
                {
                    "rel": rel,
                    "size": st.st_size,
                    "mtime": int(st.st_mtime),
                }
            )
        return enriched

    @app.callback(
        Output("file-dropdown", "options"),
        Input("file-list", "data"),
        Input("show-subfolders", "value"),
    )
    def populate_dropdown(file_list, show_flags):
        if not file_list:
            return []
        show_sub = "sub" in (show_flags or [])
        opts = []
        for item in file_list:
            rel = item["rel"]
            label = rel if show_sub else Path(rel).name
            opts.append({"label": label, "value": rel})
        return opts

    @app.callback(
        Output("dataset-key", "data"),
        Output("selected-info", "children"),
        Input("file-dropdown", "value"),
        prevent_initial_call=True,
    )
    def handle_selection(rel_value):
        if not rel_value:
            return no_update
        abs_p = safe_abs_path(rel_value)
        dataset_id = str(uuid.uuid4())  # generate a random ID for the dataset we're about to load
        # TODO: Would be nice to enable some kind of actual caching here, so that we do not re-load the data if the user re-selects a dataset...
        try:
            st = abs_p.stat()
            data_dfs = load_seurat_rds(
                abs_p
            )  # Don't send the object to the browser; just confirm and store downstream.
            cache.set(
                dataset_id, data_dfs, timeout=None
            )  # store it in the cache, timeout=None or 0 => use default (=> no expiry)

            global metadata_df, gene_matrix_df
            gene_matrix_df = data_dfs["gene_counts"]
            metadata_df = data_dfs["metadata"]

            return dataset_id, dbc.Alert(
                [
                    html.Strong("Loaded: "),
                    html.Code(str(abs_p)),
                    html.Br(),
                    f"Size: {st.st_size / 1_048_576:.2f} MB · Modified: {time.ctime(st.st_mtime)}",
                ],
                color="success",
                dismissable=True,
            )
        except Exception as e:
            return dataset_id, dbc.Alert(f"Failed to load: {e}", color="danger", dismissable=True)

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
        Output("filter-offcanvas", "is_open"),
        Input("open-filter-offcanvas", "n_clicks"),
        State("filter-offcanvas", "is_open"),
    )
    def toggle_offcanvas(n_clicks, is_open):
        if n_clicks:
            return not is_open
        return is_open

    @app.callback(
        Output("plot-container", "children"),
        Output("error-message", "children"),
        Input("plot-selector", "value"),
        Input("gene-selector", "value"),
        Input("cell-type-filter", "value"),
        Input("dataset-key", "data"),
        prevent_initial_call=True,
    )
    def update_plots(plot_type, selected_genes, selected_cell_types, dataset_key):
        global last_figure  # Store last figure for export

        if selected_genes is None or len(selected_genes) == 0:
            selected_genes = gene_matrix_df.index
        if selected_cell_types is None or len(selected_cell_types) == 0:
            selected_cell_types = metadata_df["seurat_clusters"].unique()

        filtered_cells = metadata_df.index[metadata_df["seurat_clusters"].isin(selected_cell_types)]
        filtered_expression = get_filtered_data(selected_genes, selected_cell_types)

        plot_figures = []

        try:
            if plot_type == "boxplot" and len(selected_genes) <= settings.max_features:
                df_melted = filtered_expression.melt(var_name="Cell", value_name="Expression")
                df_melted["CellType"] = df_melted["Cell"].map(metadata_df["seurat_clusters"])
                df_melted["Gene"] = np.tile(selected_genes, len(df_melted) // len(selected_genes))

                if len(selected_genes) <= settings.max_features:
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
                umap_df = cache.get(dataset_key)["umap"]  # Get umap data from cache
                last_figure = px.scatter(
                    umap_df.loc[filtered_cells],
                    x="UMAP_1",
                    y="UMAP_2",
                    color=metadata_df.loc[filtered_cells, "seurat_clusters"],
                    title="UMAP Scatterplot",
                )
                plot_figures.append(html.Div(dcc.Graph(figure=last_figure), style={"width": "100%"}))

            elif plot_type == "violin" and len(selected_genes) <= settings.max_features:
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
                if len(selected_genes) > settings.max_features:
                    last_figure.update_yaxes(showticklabels=False)
                if len(filtered_expression.columns) > 2 * settings.max_features:
                    last_figure.update_xaxes(showticklabels=False)

                plot_figures.append(
                    html.Div(dcc.Graph(figure=last_figure, style={"height": "70vh"}), style={"width": "100%"})
                )

            else:
                if len(selected_genes) == len(gene_matrix_df.index):
                    raise ValueError("Please select one or more features.")
                elif len(selected_genes) > settings.max_features:
                    raise ValueError(f"Please select no more than {settings.max_features} features.")
                else:
                    raise ValueError("Something went wrong?")

        except ValueError as e:
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
        return dcc.send_bytes(encoded_svg, filename="plot.svg")  # type: ignore


def scan_files():
    """Return a sorted list of relative file paths under BASE_DIR with allowed extensions."""
    out = []
    for root, _, files in os.walk(settings.BASE_DIR):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in settings.RDS_ALLOWED_EXT:
                rel = p.resolve().relative_to(settings.BASE_DIR)
                out.append(str(rel).replace(os.sep, "/"))
    out.sort()
    return out


def safe_abs_path(rel_path: str) -> Path:
    """Resolve a user-chosen relative path into an absolute path under BASE_DIR safely."""
    abs_p = (settings.BASE_DIR / rel_path).resolve()
    if not str(abs_p).startswith(str(settings.BASE_DIR)):  # prevent path traversal
        raise ValueError("Invalid path selection")
    return abs_p
