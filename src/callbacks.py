import base64
import io
import json
import logging
import os
import time
import uuid
from pathlib import Path

import dash_bootstrap_components as dbc
import plotly.express as px
import yaml
from dash import ALL, Input, Output, State, ctx, dcc, html, no_update
from dash.dcc.express import send_string
from flask_caching import Cache

import settings
from data_loader import load_seurat_rds
from layout import make_filter_component

# Store the last generated figure
last_figure = None

# Activate logging
logger = logging.getLogger(__name__)

def register_callbacks(app):
    # Initialize Flask-Caching **after** app creation
    cache = Cache(config={"CACHE_TYPE": "simple", "CACHE_DEFAULT_TIMEOUT": settings.CACHE_DEFAULT_TIMEOUT})
    cache.init_app(app.server)

    @app.callback(
        Output("file-list", "data"),
        Input("rescan", "n_clicks"),
        Input("init", "n_intervals"),
        prevent_initial_call=True,
    )
    def refresh_file_list(_clicks, _init):
        """
        Triggers when the 'rescan' button is clicked to refresh the list of available files in the data directory.
        Also triggers on app initialization to populate the file list on startup.
        
        :param _clicks: Description
        :param _init: Description
        """
        base_dir = Path(os.getenv("DATASCOPE_RDS_PATH", settings.DEFAULT_RDS_PATH))
        files = scan_files(base_dir)
        # maybe include simple metadata (mtime, size)?
        enriched = []
        for rel in files:
            p = (base_dir / rel).resolve()
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
        """
        Populate the file dropdown options based on the scanned file list and the "show subfolders" flag.
        If "show subfolders" is enabled, show full relative paths; otherwise, show only filenames.
        
        :param file_list: Description
        :param show_flags: Description
        """
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
        Output("plot-selector", "disabled"),
        Output("selected-info", "children"),
        Input("file-dropdown", "value"),
        prevent_initial_call=True,
    )
    def handle_file_selection(rel_value):
        """
        Triggered when a file is selected from the dropdown. Loads the selected Seurat RDS file, extracts the filter
        schema from its metadata, and updates the dataset key and UI state accordingly.
        
        :param rel_value: Description
        """
        if not rel_value:
            return no_update  # If no file selected, do nothing
        str_path = Path(os.getenv("DATASCOPE_RDS_PATH", settings.DEFAULT_RDS_PATH))
        abs_path = (str_path / rel_value).resolve()
        if not str(abs_path).startswith(str(str_path)):  # prevent path traversal
            raise ValueError(f"Invalid path selection - {abs_path}")
        dataset_key = str(uuid.uuid4())  # generate a random ID for the dataset we're about to load
        # TODO: Would be nice with actual caching here, so that we do not re-load if the user re-selects a dataset...
        # And/or clering the cache so we don't use too much memory over time.
        try:
            st = abs_path.stat()
            data_dfs = load_seurat_rds(abs_path)  # Don't send this object to the browser
            cache.clear()  # Clear previous cache to save memory
            cache.set(
                dataset_key, data_dfs, timeout=None
            )  # store big data_dfs in the cache, timeout=None or 0 => use default (=> no expiry)
            filter_schema = filter_from_metadata(data_dfs["metadata"])
            return (
                dataset_key,
                filter_schema,  # filter schema from metadata
                False,  # Enable plot selector after file load
                dbc.Alert(
                    [
                        html.Strong("Loaded: "),
                        html.Code(str(abs_path)),
                        html.Br(),
                        f"Size: {st.st_size / 1_048_576:.2f} MB · Modified: {time.ctime(st.st_mtime)}",
                    ],
                    color="success",
                    dismissable=True,
                ),
            )
        except Exception as e:
            return dataset_key, {}, True, dbc.Alert(f"Failed to load: {e}", color="danger", dismissable=True)


    @app.callback(
        Output("open-left-offcanvas", "disabled"),
        Input("plot-selector", "value"),
    )
    def toggle_gene_selector(plot_type):
        # List of plots that should show the gene selector
        plots_showing_genes = ["boxplot", "violin", "heatmap"]  # Update as needed
        if plot_type in plots_showing_genes:
            return False
        else:
            return True

    @app.callback(
        Output("filter-left-offcanvas", "is_open"),
        Input("open-left-offcanvas", "n_clicks"),
        State("filter-left-offcanvas", "is_open"),
    )
    def toggle_left_offcanvas(n_clicks, is_open):
        if n_clicks:
            return not is_open
        return is_open

    @app.callback(
        Output("filter-right-offcanvas", "is_open"),
        Input("open-right-offcanvas", "n_clicks"),
        State("filter-right-offcanvas", "is_open"),
    )
    def toggle_right_offcanvas(n_clicks, is_open):
        if n_clicks:
            return not is_open
        return is_open

    @app.callback(
        Output("barcode-filters", "children"),
        Input("filter-schema-store", "data"),
    )
    def build_barcode_filter_components(schema):
        if not schema:
            return html.Div("No filters defined.")
        headline = dbc.Row(
            [
                dbc.Col([], xs=9),  # Empty cell for spacing
                dbc.Col(
                    html.Div("Color", style={"transform": "rotate(45deg)", "display": "inline-block"}),
                    xs=1,
                ),
                dbc.Col(
                    html.Div("Shape", style={"transform": "rotate(45deg)", "display": "inline-block"}),
                    xs=1,
                ),
                dbc.Col([], xs=1),  # Empty cell for spacing
            ]
        )
        return [headline] + [make_filter_component(f) for f in schema]


    @app.callback(
        Output("download-config", "data"),
        Input("save-config-btn", "n_clicks"),
        State("gene-selector", "value"),
        State({"type": "filter-control", "name": ALL}, "value"),
        State({"type": "filter-control", "name": ALL}, "id"),
        State("color-column-name", "data"),
        State("shape-column-name", "data"),
        State("file-dropdown", "value"),
        prevent_initial_call=True,
    )
    def save_config_yaml(n_clicks, selected_genes, filter_values, filter_ids, color_col, shape_col, rel_dataset):
        if not n_clicks:
            return no_update

        # Turn the pattern-matching filter controls into a dict: {column_name: value}
        filters = {}
        for v, id_ in zip(filter_values or [], filter_ids or [], strict=False):
            name = id_.get("name")
            if name is None:
                continue
            # store only "active" filters (optional; remove this if you want everything)
            if v not in (None, [], ""):
                filters[name] = v

        payload = {
            "version": 1,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dataset": rel_dataset,          # relative path from dropdown (nice to keep)
            "Genes": selected_genes or [],   # matches what your upload logic expects
            "Filters": filters,
            "Color": color_col,
            "Shape": shape_col,
        }

        yaml_text = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)

        # Friendly filename
        base = Path(rel_dataset).stem if rel_dataset else "config"
        filename = f"{base}.filters.yaml"

        return send_string(yaml_text, filename=filename)

    @app.callback(
        Output("plot-container", "children"),
        Output("error-message", "children"),
        Input("plot-selector", "value"),
        Input("gene-selector", "value"),
        Input("cell-index-key", "data"),
        Input("shape-column-name", "data"),
        Input("dataset-key", "data"),
        prevent_initial_call=True,
    )
    def update_plots(plot_type, selected_genes, cell_index_key, shape_column, dataset_key):
        global last_figure  # Store last figure for export
        plot_figures = []

        # TODO: The wrapping for plots is partially broken for vertical resizing of the window.
        # TODO: Heatmap brug Z-scores på gener
        # TODO: Mulighed for at uploade gen-lister
        #   Vi skal update Input("gene-selector", "value") med værdier fra filen, og så vil plot-opdateringen trigge
        #   automatisk. Vi skal bare parse filen og få de rigtige gen-navne ud.
        #   Det kan gøres, det skal faktisk gøres, i callback til upload-komponenten.
        # TODO: Fix the download of plots (currently downloads last one, not all)

        seurat_data = cache.get(dataset_key)  # Get seurat data from cache
        cell_index = cache.get(cell_index_key)  # Get cell index data from cache
        if seurat_data is None or cell_index is None:
            # Data not (yet?) loaded or cache expired
            return [], dbc.Alert(
                f"No data loaded or timeout exceeded (timeout = {settings.CACHE_DEFAULT_TIMEOUT} Seconds). "
                + "Please (re-)load the dataset.",
                color="danger",
                dismissable=True,
            )

        try:
            selected_barcodes = cell_index["index"]  # Get filtered cell/barcodes indices from cache
            barcodes_color = cell_index["color"]  # Get colors matching index from cache
            barcodes_shape = cell_index["shape"]  # Get shapes matching index from cache
            if plot_type == "boxplot":
                """Generate boxplots for each selected gene. Either split by shape filter, or all in one stack."""
                if not selected_genes:
                    raise ValueError("For Boxplots please select one or more features.")
                elif len(selected_genes) > settings.max_features:
                    raise ValueError(f"For Boxplots please select no more than {settings.max_features} features.")
                boxplot_df = seurat_data["boxplot"]  # Get boxplot data from seurat data in cache
                for gene in selected_genes:
                    last_figure = generate_boxplot(boxplot_df, selected_barcodes, shape_column, gene, barcodes_color)
                    plot_figures.append(
                        html.Div(
                            dcc.Graph(figure=last_figure),
                            style={"width": "49%", "height": "450px", "display": "inline-block"},
                        )
                    )

            elif plot_type == "umap":
                umap_df = cache.get(dataset_key)["umap"]  # Get umap data from cache
                last_figure = px.scatter(
                    umap_df.loc[selected_barcodes],
                    x="UMAP_1",
                    y="UMAP_2",
                    color=barcodes_color,
                    symbol=barcodes_shape,
                    title="UMAP Scatterplot",
                )
                plot_figures.append(
                    html.Div(
                        dcc.Graph(figure=last_figure, style={"height": "100%", "width": "100%"}),
                        style={"flex": "1 1 auto", "minHeight": 0, "minWidth": 0},
                    )
                )

            elif plot_type == "violin" and len(selected_genes) <= settings.max_features:
                """Generate violin plots for each selected gene. Either split by shape filter, or all in one stack."""
                if not selected_genes:
                    raise ValueError("For Violin plots please select one or more features.")
                elif len(selected_genes) > settings.max_features:
                    raise ValueError(f"For Violin plots please select no more than {settings.max_features} features.")

                violin_df = (
                    seurat_data["boxplot"]
                    .loc[selected_barcodes, selected_genes]
                    .melt(var_name="Gene", value_name="Expression")
                )
                if barcodes_color is not None:
                    color_for_plot = barcodes_color[selected_barcodes].to_list() * len(selected_genes)
                else:
                    color_for_plot = None

                last_figure = px.violin(
                    violin_df,
                    x="Gene",
                    y="Expression",
                    color=color_for_plot,
                    labels={shape_column: shape_column, "value": "Expression"},
                    box=True,
                    points="all",
                    title="Violin Plot",
                )
                if len(selected_genes) <= 50:
                    plot_figures.append(html.Div(dcc.Graph(figure=last_figure), style={"width": "100%"}))

            elif plot_type == "heatmap":
                selected_genes = selected_genes or seurat_data["heatmap"].index.tolist()  # Default to all genes
                heatmap_df = seurat_data["heatmap"].loc[selected_genes, selected_barcodes]  # Get gene count data
                last_figure = px.imshow(
                    heatmap_df,
                    color_continuous_scale="Viridis",
                    title="Gene Expression Heatmap",
                    x=heatmap_df.columns,  # columns
                    y=selected_genes,  # rows
                    aspect="auto",
                    # aspect="equal",
                    labels=dict(x="Cells", y="Genes", color="Expr"),  # axis titles & color-bar
                )

                # Don't show labels if there's too many
                if len(selected_genes) > settings.max_features:
                    last_figure.update_yaxes(showticklabels=False)
                if len(selected_barcodes) > 2 * settings.max_features:
                    last_figure.update_xaxes(showticklabels=False)

                plot_figures.append(
                    html.Div(dcc.Graph(figure=last_figure), style={"flex": "1 1 auto", "minHeight": 0, "minWidth": 0})
                )

            else:
                raise ValueError("Something went wrong?")

        except ValueError as e:
            return plot_figures, dbc.Alert(f"Error: {e}", color="danger", dismissable=True)
        except TypeError as e:
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

    register_offcanvas_callbacks(app, cache)


def register_offcanvas_callbacks(app, cache):
    """Stuff relating to the offcanvas drawers for filters and config upload."""
    @app.callback(
        Output("gene-selector", "options"),
        Output("gene-selector", "value"),
        Input("dataset-key", "data"),
        State("gene-selector", "value"),
        Input("config-store", "data"),
    )
    def update_gene_selection(dataset_key, selected_genes, config_data):
        """
        Update the gene selector drop-down based on the selected dataset. Validates the currently selected genes
        against the new options and resets selection if they are no longer valid.
        
        :param dataset_key: Description
        :param selected_genes: Description
        """
        try:
            gene_matrix_df = cache.get(dataset_key)["gene_counts"]  # Get gene count data from seurat data in cache
            gene_options = [{"label": gene, "value": gene} for gene in gene_matrix_df.index]
        except TypeError:
            return no_update, no_update

        # This is a bit hacky, but it allows us to set the gene selection based on an uploaded config file.
        # Could be added to the plot update callback, but that one is already bloated. This should work
        if config_data and "Genes" in config_data:
            config_genes = config_data["Genes"] # Get gene list from uploaded config
            selected_genes = config_genes

        # Validate selected genes columns against gene_options (which may change if user re-loads dataset)
        set_gene_options = set([opt["value"] for opt in gene_options])  # O(1) lookups
        selected_genes = [x for x in selected_genes if x in set_gene_options]

        return gene_options, selected_genes

    @app.callback(
        Output("cell-index-key", "data"),
        Input({"type": "filter-control", "name": ALL}, "value"),
        State({"type": "filter-control", "name": ALL}, "id"),
        Input("color-column-name", "data"),
        Input("shape-column-name", "data"),
        Input("dataset-key", "data"),
        Input("filter-schema-store", "data"),
        Input("config-store", "data"),
    )
    def update_barcode_selection(filters_cells, filters_ids, color_column, shape_column, dataset_key, schema, config_data):
        try:
            metadata_df = cache.get(dataset_key)["metadata"]  # Get metadata data from seurat data in the cache.
            selected_cells = metadata_df.index  # Default to all cell types
        except TypeError:
            return no_update

#        # Set the barcode/cell selection based on an uploaded config file.
#        if config_data and  in config_data:
#            config_genes = config_data["Genes"] # Get gene list from uploaded config
#            selected_cells = config_genes

        # Validate color/shape columns against schema (Schema may be changed if user re-loaded dataset)
        schema_names = [s["name"] for s in schema]
        if color_column not in schema_names:
            color_column = None
        if shape_column not in schema_names:
            shape_column = None

        for f, id_ in zip(filters_cells, filters_ids, strict=True):
            selected_indices = metadata_df.index[metadata_df[id_["name"]].isin(f)]
            if selected_indices.size:
                selected_cells = selected_cells.intersection(selected_indices)
        color_barcodes = metadata_df.loc[selected_cells, color_column] if color_column else None  # Series or None
        shape_barcodes = metadata_df.loc[selected_cells, shape_column] if shape_column else None  # Series or None

        selection_id = str(uuid.uuid4())  # generate a random ID for the selection we're about to store
        cache.set(
            selection_id, {"index": selected_cells, "color": color_barcodes, "shape": shape_barcodes}, timeout=None
        )  # store it in the cache, timeout=None or 0 => use default (=> no expiry)
        # TODO: I'm guessing we may have a memory leak here if the user keeps changing selections a lot?
        # Every time we create a new selection_id we store it in the cache, but never delete old ones.
        # I'm currently wiping the cache every time the user loads a new dataset. That helps.

        return selection_id

    @app.callback(
        Output({"type": "color-control", "name": ALL}, "value"),
        Output("color-column-name", "data"),
        Input({"type": "color-control", "name": ALL}, "value"),
        prevent_initial_call=True,
    )
    def exclusive_color_selection(color_button):
        single_select = [[]] * len(color_button)
        try:
            triggered = ctx.triggered_id.name  # type: ignore # which item triggered the callback
            single_select[color_button.index([triggered])] = [triggered]
        except (AttributeError, ValueError):
            return single_select, None  # If nothing selected
        return single_select, triggered

    @app.callback(
        Output({"type": "shape-control", "name": ALL}, "value"),
        Output("shape-column-name", "data"),
        Input({"type": "shape-control", "name": ALL}, "value"),
        prevent_initial_call=True,
    )
    def exclusive_shape_selection(shape_button):
        single_select = [[]] * len(shape_button)
        try:
            triggered = ctx.triggered_id.name  # type: ignore # which item triggered the callback
            single_select[shape_button.index([triggered])] = [triggered]
        except (AttributeError, ValueError):
            return single_select, None  # If nothing selected
        return single_select, triggered

    @app.callback(
        Output("config-store", "data"),
        Output("upload-status", "children"),
        Input("upload-config", "contents"),
        State("upload-config", "filename"),
        prevent_initial_call=True,
    )
    def on_config_upload(contents, filename):
        """
        Triggers when a config or filter file is selected in dialog. Parses the uploaded file and stores its content in
        the dcc.Store component for use in other callbacks. Also updates the upload status message based on success or
        failure of the upload.
        
        :param contents: Description
        :param filename: Description
        """
        if not contents:
            return no_update, no_update
        try:
            data = parse_upload(contents, filename)
            return data, f"Loaded: {filename}"
        except Exception as e:
            return no_update, f"Upload failed: {e}"



# -------------------------------------------------------------------
# Helper to generate a boxplot figure
def generate_boxplot(boxplot_df, selected_barcodes, shape_column, gene, barcodes_color):
    """Generate a boxplot figure."""
    if shape_column and shape_column in boxplot_df.columns:  # If shape column is specified and exists
        fig = px.box(
            boxplot_df.loc[selected_barcodes, [shape_column, gene]],
            x=shape_column,
            y=gene,
            color=barcodes_color[selected_barcodes] if barcodes_color is not None else None,
            labels={shape_column: shape_column, gene: "Expression"},
            title=f"Boxplot for {gene}",
        )
    else:
        fig = px.box(  # If no shape column, plot all in one box
            boxplot_df.loc[selected_barcodes, gene],
            y=gene,
            labels={gene: "Expression"},
            color=barcodes_color[selected_barcodes] if barcodes_color is not None else None,
            title=f"Boxplot for {gene}",
        )
    return fig


# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper to build the filter schema from the metadata
def filter_from_metadata(metadata_df):
    filter_schema = []
    for series in [metadata_df[c] for c in metadata_df.columns]:  # Loop over series in metadata data frame
        if series.dtype in ["category"]: # Note that some types convert to category in data_loader.py
            f = {
                "name": series.name,
                "label": series.name,
                "type": "categorical",
                "values": sorted(series.unique()),
                "default": [],  # empty means "no filter selected"
            }
        elif series.dtype in ["int64", "float64", "int32", "float32"]:
            f = {
                "name": series.name,
                "label": series.name,
                "type": "numeric_range",
                "min": int(series.min()),
                "max": int(series.max()),
                "step": 100,
                "default": [],
            }
        else:
            continue  # Skip unsupported types
        filter_schema.append(f)
    return filter_schema


# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper to scan data directory for allowed files
def scan_files(dir_path: Path) -> list[str]:
    """Return a sorted list of relative file paths under dir_path with allowed extensions."""
    out = []
    for root, _, files in os.walk(dir_path):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in settings.RDS_ALLOWED_EXT:
                rel = p.resolve().relative_to(dir_path)
                out.append(str(rel).replace(os.sep, "/"))
    out.sort()
    return out


# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper to parse uploaded config/filter files
def parse_upload(contents: str, filename: str):
    """
    contents is like: 'data:application/json;base64,AAAA...'
    returns python object (dict/list/...) you can store in dcc.Store
    """
    _, b64data = contents.split(",", 1)
    raw = base64.b64decode(b64data)

    # JSON is nice for simple key-value configs, and it's also widely used and supported.
    if filename.lower().endswith(".json"):
        return json.loads(raw.decode("utf-8"))

    # YAML is nice because it can represent complex data structures, and it's also human-readable.
    if filename.lower().endswith((".yaml", ".yml")):
        return yaml.safe_load(raw.decode("utf-8"))

    # If not YAML or JSON, allow plain text filters for the 'Genes' slot
    if filename.lower().endswith(".txt"):
        return {"Genes": raw.decode("utf-8")}

#    raise ValueError(f"Unsupported file type: {filename}")
    raise ValueError(f"Config: {yaml.safe_load(raw.decode('utf-8'))}")
# -------------------------------------------------------------------
