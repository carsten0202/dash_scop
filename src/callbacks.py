import io
import os
import time
import uuid
from pathlib import Path

import dash_bootstrap_components as dbc
import numpy as np
import plotly.express as px
from dash import ALL, Input, Output, State, ctx, dcc, html, no_update
from flask_caching import Cache

import settings
from data_loader import load_seurat_rds
from layout import make_filter_component

# Store the last generated figure
last_figure = None


def register_callbacks(app):
    # Initialize Flask-Caching **after** app creation
    cache = Cache(config={"CACHE_TYPE": "simple"})
    cache.init_app(app.server)

    @cache.memoize()
    def get_filtered_data(selected_genes, selected_cell_types, metadata_df, gene_matrix_df):
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
        Output("filter-schema-store", "data"),
        Output("selected-info", "children"),
        Input("file-dropdown", "value"),
        prevent_initial_call=True,
    )
    def handle_file_selection(rel_value):
        if not rel_value:
            return no_update
        abs_p = safe_abs_path(rel_value)
        dataset_id = str(uuid.uuid4())  # generate a random ID for the dataset we're about to load
        #        filter_schema = []  # Initialize the filtering schema to empty (no filters)
        # TODO: Would be nice to enable some kind of actual caching here, so that we do not re-load the data if the user re-selects a dataset...
        try:
            st = abs_p.stat()
            data_dfs = load_seurat_rds(abs_p)  # Don't send this object to the browser
            cache.set(
                dataset_id, data_dfs, timeout=None
            )  # store big data_dfs in the cache, timeout=None or 0 => use default (=> no expiry)
            filter_schema = filter_from_metadata(data_dfs["metadata"])

            return (
                dataset_id,
                filter_schema,
                dbc.Alert(
                    [
                        html.Strong("Loaded: "),
                        html.Code(str(abs_p)),
                        html.Br(),
                        f"Size: {st.st_size / 1_048_576:.2f} MB · Modified: {time.ctime(st.st_mtime)}",
                    ],
                    color="success",
                    dismissable=True,
                ),
            )
        except Exception as e:
            return dataset_id, {}, dbc.Alert(f"Failed to load: {e}", color="danger", dismissable=True)

    @app.callback(
        Output("cell-index-key", "data"),
        Input({"type": "filter-control", "name": ALL}, "value"),
        State({"type": "filter-control", "name": ALL}, "id"),
        Input("color-column-name", "data"),
        Input("shape-column-name", "data"),
        Input("dataset-key", "data"),
    )
    def update_barcode_selection(filters_cells, filters_ids, color_column, shape_column, dataset_key):
        try:
            metadata_df = cache.get(dataset_key)["metadata"]  # Get metadata data from seurat data in the cache.
            selected_cells = metadata_df.index  # Default to all cell types
        except TypeError:
            return no_update

        for f, id_ in zip(filters_cells, filters_ids):
            selected_indices = metadata_df.index[metadata_df[id_["name"]].isin(f)]
            if selected_indices.size:
                selected_cells = selected_cells.intersection(selected_indices)
        color_barcodes = metadata_df.loc[selected_cells, color_column] if color_column else None  # Series or None
        shape_barcodes = metadata_df.loc[selected_cells, shape_column] if color_column else None  # Series or None

        selection_id = str(uuid.uuid4())  # generate a random ID for the selection we're about to store
        cache.set(
            selection_id, {"index": selected_cells, "color": color_barcodes, "shape": shape_barcodes}, timeout=None
        )  # store it in the cache, timeout=None or 0 => use default (=> no expiry)
        # TODO: I'm guessing we may have a memory leak here if the user keeps changing selections a lot?
        # Every time we create a new selection_id and store it in the cache, but never delete old ones.

        return selection_id

    # TODO: This guy is getting old. Will need to delete or rewrite when the drawer is operational.
    @app.callback(
        Output("gene-selector", "options"),
        Input("dataset-key", "data"),
        prevent_initial_call=True,
    )
    def update_gene_selection(dataset_key):
        gene_matrix_df = cache.get(dataset_key)["gene_counts"]  # Get gene count data from seurat data in cache
        gene_options = [{"label": gene, "value": gene} for gene in gene_matrix_df.index]
        return gene_options

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
        Output("all-filters", "children"),
        Input("filter-schema-store", "data"),
    )
    def build_filter_components(schema):
        if not schema:
            return html.Div("No filters defined.")
        return [make_filter_component(f) for f in schema]

    @app.callback(
        Output("plot-container", "children"),
        Output("error-message", "children"),
        Input("plot-selector", "value"),
        Input("gene-selector", "value"),
        Input("cell-index-key", "data"),
        Input("dataset-key", "data"),
        prevent_initial_call=True,
    )
    def update_plots(plot_type, selected_genes, cell_index_key, dataset_key):
        global last_figure  # Store last figure for export

        # TODO: Phase out this code
        seurat_data = cache.get(dataset_key)  # Get seurat data from cache
        metadata_df = seurat_data["metadata"]  # Get metadata data from seurat
        gene_matrix_df = seurat_data["gene_counts"]  # Get gene count data from seurat
        selected_cell_types = metadata_df.index  # Default to all cell types
        if selected_genes is None or len(selected_genes) == 0:
            selected_genes = gene_matrix_df.index
        filtered_expression = gene_matrix_df.loc[selected_genes, selected_cell_types]
        # get_filtered_data(selected_genes, selected_cell_types, metadata_df, gene_matrix_df)

        filtered_cells = cache.get(cell_index_key)["index"]  # Get filtered cell indices from cache
        cells_color = cache.get(cell_index_key)["color"]  # Get color column from cache

        print("filtered_cells:", filtered_cells)
        print("cells_color:", cells_color)

        plot_figures = []

        # TODO: boxplots and violin plots are no longer working correctly
        # TODO: And the heatmap doesn't work either...

        try:
            if plot_type == "boxplot" and len(selected_genes) <= settings.max_features:
                """Generate boxplots for each selected gene. Either split by color filter, or all in one stack."""

                boxplot_df = seurat_data["boxplot"]
                selected_barcodes = filtered_cells

                for gene in selected_genes:
                    df = boxplot_df.loc[selected_barcodes, [cells_color, gene]]

                    last_figure = px.box(
                        df,
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
                    color=cells_color,
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

    register_helper(app)


def register_helper(app):
    @app.callback(
        Output({"type": "color-control", "name": ALL}, "value"),
        Output("color-column-name", "data"),
        Input({"type": "color-control", "name": ALL}, "value"),
        prevent_initial_call=True,
    )
    def exclusive_color_selection(color_button):
        single_select = [None] * len(color_button)
        try:
            triggered = ctx.triggered_id.name  # which item triggered the callback
            single_select[color_button.index(triggered)] = triggered
        except (AttributeError, ValueError):
            return no_update  # If nothing selected

        return single_select, triggered

    @app.callback(
        Output({"type": "shape-control", "name": ALL}, "value"),
        Output("shape-column-name", "data"),
        Input({"type": "shape-control", "name": ALL}, "value"),
        prevent_initial_call=True,
    )
    def exclusive_shape_selection(shape_button):
        single_select = [None] * len(shape_button)
        try:
            triggered = ctx.triggered_id.name  # which item triggered the callback
            single_select[shape_button.index(triggered)] = triggered
        except (AttributeError, ValueError):
            return no_update  # If nothing selected

        return single_select, triggered


# -------------------------------------------------------------------
# Helper to build the filter schema from the metadata
def filter_from_metadata(metadata_df):
    filter_schema = []
    for series in [metadata_df[c] for c in metadata_df.columns]:  # Loop over series in metadata data frame
        if series.dtype in ["object", "category"]:
            f = {
                "name": series.name,
                "label": "Seurat@meta.data$" + series.name,
                "type": "categorical",
                "values": sorted(series.unique()),
                "default": [],  # empty means "no filter selected"
            }
        else:
            f = {}
        filter_schema.append(f)
    return filter_schema


# -------------------------------------------------------------------


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
