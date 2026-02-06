import os

import dash_bootstrap_components as dbc
from dash import dcc, html


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
        html.Div(
            id="file-controls",
            children=[
                html.H1("DataSCOPe: Visualization of Data from Single-Cell Omics Projects"),
                dbc.Col(
                    [
                        dbc.Button("Rescan", id="rescan", n_clicks=0),
                        dcc.Dropdown(
                            id="file-dropdown",
                            options=[],  # filled by callback
                            placeholder=f"Browse {os.getenv('DASH_RDS_PATH', os.getcwd())}…",
                            searchable=True,
                            clearable=False,
                            style={"flex": "1"},
                        ),
                        dbc.Checklist(
                            options=[{"label": "Show subfolders", "value": "sub"}],
                            value=["sub"],
                            id="show-subfolders",
                            switch=True,
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexDirection": "row",  # horizontal stacking
                        "alignItems": "center",  # vertical alignment
                        "gap": "0.5rem",  # spacing between elements
                    },
                ),
                html.Div(id="selected-info", className="mt-3"),
                dcc.Interval(id="init", interval=50, n_intervals=0, max_intervals=1),  # populate once on load
            ],
        ),
        # Dropdown for selecting the plot type
        html.Label("Select a plot type:"),
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
        ),
        # Download button and component
        dbc.Row(
            [
                dbc.Col(dbc.Button("Gene Filter Panel", id="open-left-offcanvas", n_clicks=0, disabled=True), width=2),
                dbc.Col(
                    dbc.Button(
                        "Download Plot as SVG", id="download-btn", n_clicks=0, disabled=True, style={"display": "none"}
                    ),
                    width=2,
                ),
                dbc.Col(dbc.Button("Barcode Filter Panel", id="open-right-offcanvas", n_clicks=0), width=2),
            ],
            justify="center",
        ),
        dcc.Download(id="download-plot"),
        html.Div(id="error-message", className="mt-3"),
        # Graph container
        html.Div(
            id="plot-container",
            style={
                "display": "flex",
                "flex": "1 1 auto",
                "minHeight": 0,
                "minWidth": 0,
                "flexWrap": "wrap",
                "gap": "1rem",
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
            dcc.Upload(
                id="upload-config",
                children=html.Button("Upload config / filter file"),
                multiple=False,  # single file
            ),
            html.Div(id="upload-status", style={"marginTop": "0.75rem"}),
            dcc.Store(id="config-store"),  # parsed config lives here
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
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Dropdown(
                                id=filter_id,
                                options=[{"label": v, "value": v} for v in f["values"]],
                                multi=True,
                                value=f.get("default", []),
                                placeholder=f"Select {f['label'].lower()}",
                            ),
                            xs=9,
                        ),
                        dbc.Col(
                            dcc.Checklist(id=color_id, options=[{"label": "", "value": f["name"]}], value=[]),
                            xs=1,
                        ),
                        dbc.Col(
                            dcc.Checklist(id=shape_id, options=[{"label": "", "value": f["name"]}], value=[]),
                            xs=1,
                        ),
                        dbc.Col([], xs=1),  # Empty cell for spacing
                    ]
                ),
            ],
            style={"marginBottom": "1rem", "alignItems": "right"},
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
