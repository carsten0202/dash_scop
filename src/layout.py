import os

import dash_bootstrap_components as dbc
from dash import dcc, html

FILTER_GRID_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "minmax(0, 1fr) 2rem 2rem",
    "columnGap": "0.5rem",
    "rowGap": "0.25rem",
    "alignItems": "center",
}


# -------------------------------------------------------------------
# Main layout function
def get_layout(config_data):
    layout = [
        dcc.Store(id="cell-index-key"),  # holds just the key string for the current cell index selection
        dcc.Store(id="color-column-name"),  # holds column name for the current color selection
        dcc.Store(id="dataset-key"),  # holds just the key string for the current dataset
        dcc.Store(id="file-list"),  # holds list of files
        dcc.Store(id="filter-schema-store", data=[]),  # holds the filter schema, [] for none
        dcc.Store(id="shape-column-name"),  # holds column name for the current shape selection
        dcc.Store(id="config-store"),  # parsed config lives here
        html.Div(
            id="file-controls",
            children=[
                html.H1(
                    "DataSCOPe: Visualization of Data from Single-Cell Omics Projects",
                    style={"marginBottom": "0.75rem"},
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Label("Data source:", style={"marginBottom": 0, "fontWeight": 600}),
                                dbc.Button("Rescan", id="rescan", n_clicks=0, color="primary"),
                                dbc.Checklist(
                                    options=[{"label": "Subfolders", "value": "sub"}],
                                    value=["sub"],
                                    id="show-subfolders",
                                    switch=True,
                                ),
                                dcc.Dropdown(
                                    id="file-dropdown",
                                    options=[],  # filled by callback
                                    placeholder=f"Browse {os.getenv('DASH_RDS_PATH', os.getcwd())}…",
                                    searchable=True,
                                    clearable=False,
                                    style={"flex": "1 1 560px", "minWidth": "420px"},
                                ),
                                dcc.Download(id="download-config"),  # download target
                                dcc.Upload(
                                    id="upload-config",
                                    children=dbc.Button(
                                        "Upload filters", id="upload-config-btn", n_clicks=0, color="primary"
                                    ),
                                    multiple=False,  # single file
                                ),
                                dbc.Button("Save filters", id="save-config-btn", n_clicks=0, color="primary"),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "0.75rem",
                                "flexWrap": "wrap",
                            },
                        ),
                    ],
                    style={
                        "padding": "0.75rem 1rem",
                        "borderRadius": "0.75rem",
                        "background": "rgba(255,255,255,0.6)",
                        "backdropFilter": "blur(6px)",
                        "marginBottom": "0.5rem",
                        "position": "relative",
                        "zIndex": 20,
                    },
                ),
                dcc.Interval(id="init", interval=50, n_intervals=0, max_intervals=1),  # populate once on load
            ],
        ),
        # Dropdown for selecting the plot type
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Select a plot type:", style={"marginBottom": 0, "fontWeight": 600}),
                        dcc.Dropdown(
                            id="plot-selector",
                            options=[
                                {"label": "Boxplot", "value": "boxplot"},
                                {"label": "UMAP Scatterplot", "value": "umap"},
                                {"label": "Violin Plot", "value": "violin"},
                                {"label": "Heatmap", "value": "heatmap"},
                            ],
                            value="umap",  # Default selection
                            clearable=False,  # Should never be empty. You must select one, or let the default ride.
                            disabled=True,  # Enable after file load
                            style={"flex": "1 1 560px", "minWidth": "280px"},
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "0.75rem", "flex": "1 1 520px", "minWidth": "340px"},
                ),
                html.Div(
                    [
                        dbc.Button("Gene Filter Panel", id="open-left-offcanvas", n_clicks=0, color="primary"),
                        dbc.Button("Export Plot SVG", id="download-svg-btn", n_clicks=0, color="primary"),
                        dbc.Button("Barcode Filter Panel", id="open-right-offcanvas", n_clicks=0, color="primary"),
                    ],
                    style={"display": "flex", "alignItems": "center", "gap": "0.5rem", "flexWrap": "wrap", "justifyContent": "flex-end"},
                ),
            ],
            style={
                "display": "flex",
                "alignItems": "center",
                "flexWrap": "wrap",
                "gap": "0.75rem",
                "padding": "0.5rem 0.75rem",
                "borderRadius": "0.75rem",
                "background": "rgba(255,255,255,0.6)",
                "backdropFilter": "blur(6px)",
                "marginBottom": "0.5rem",
                "position": "relative",
                "zIndex": 10,
            },
        ),
        dcc.Download(id="download-plot"),
        html.Div(
            [
                html.Div(id="load-message"),
                html.Div(id="plot-message"),
            ],
            id="message-area",
            style={
                "display": "flex",
                "flexDirection": "column",
                "gap": "0.5rem",
                "marginBottom": "0.5rem",
            },
        ),
        # Graph container
        html.Div(
            id="plot-container",
            style={
                "display": "flex",
                "flex": "1 1 auto",
                "minHeight": 0,
                "minWidth": 0,
                "flexWrap": "wrap",
                "alignContent": "flex-start",
                "gap": "1rem",
                "overflowY": "auto",
            },
        ),
        # Off-canvas drawer holding cell/barcode filters
        dbc.Offcanvas(
            id="filter-right-offcanvas",
            title="Barcode Filters",
            is_open=False,
            placement="end",
            children=html.Div(id="barcode-filters"),
            scrollable=True,
            backdrop=True,
        ),
        # Off-canvas drawer holding gene filters
        dbc.Offcanvas(
            id="filter-left-offcanvas",
            title="Gene Filters",
            is_open=False,
            placement="start",
            children=html.Div([build_left(config_data)]),
            scrollable=True,
            backdrop=True,
        ),
    ]

    return html.Div(
        layout,
        style={
            "height": "100vh",
            "width": "100vw",
            "padding": "1rem",
            "display": "flex",
            "flexDirection": "column",
            "minHeight": 0,
            "overflow": "hidden",
        },
    )


# -------------------------------------------------------------------
# Helper to build the left-side controls (offcanvas)
def build_left(config_data):
    # Multi-dropdown for gene selection
    html_div = html.Div(
        id="gene-selector-container",
        children=[
            html.Label("Select gene(s):", htmlFor="gene-selector"),
            dcc.Dropdown(
                id="gene-selector",
                options=[],  # Populated dynamically
                multi=True,
                placeholder="Select genes to display...",
                value=config_data.get("genes", []),
            ),
            html.Div(id="upload-status", style={"marginTop": "0.75rem"}),
            # layout.py (inside build_left)

        ],
    )
    return html_div
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper to build a control for a single filter definition
def make_filter_component(f):
    filter_id = {"type": "filter-control", "name": f["name"]}
    color_id = {"type": "color-control", "name": f["name"]}
    shape_id = {"type": "shape-control", "name": f["name"]}

    if f["type"] == "categorical":
        return html.Div(
            [
                html.Label(f["label"]),
                html.Div(
                    [
                        dcc.Dropdown(
                            id=filter_id,
                            options=[{"label": v, "value": v} for v in f["values"]],
                            multi=True,
                            value=f.get("default", []),
                            placeholder=f"Select {f['label'].lower()}",
                        ),
                        html.Div(
                            dcc.Checklist(id=color_id, options=[{"label": "", "value": f["name"]}], value=[]),
                            style={"justifySelf": "center"},
                        ),
                        html.Div(
                            dcc.Checklist(id=shape_id, options=[{"label": "", "value": f["name"]}], value=[]),
                            style={"justifySelf": "center"},
                        ),
                    ],
                    style=FILTER_GRID_STYLE,
                ),
            ],
            style={"marginBottom": "1rem"},
        )

    if f["type"] == "numeric_range":
        return html.Div(
            [
                html.Label(f["label"]),
                dcc.RangeSlider(
                    id=filter_id,
                    min=f["min"],
                    max=f["max"],
                    step=f["step"],
                    value=f.get("default", [f["min"], f["max"]]),
                    tooltip={"always_visible": False, "placement": "bottom"},
                ),
            ],
            className="d-none",  # FIX: Hide numeric filters for now, until supported
            style={"marginBottom": "1.5rem"},
        )

    # Fallback (you can add boolean, text, etc. later)
    return html.Div(f"Unsupported filter type: {f['type']}")
# -------------------------------------------------------------------
