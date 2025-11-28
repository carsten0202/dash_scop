import dash_bootstrap_components as dbc
from dash import dcc, html

import settings

# This is what, in your app, you'd derive from the Seurat metadata
filter_schema = [
    {
        "name": "n_genes",
        "label": "Number of genes",
        "type": "numeric_range",
        #        "min": int(df["n_genes"].min()),
        "min": 0,
        #        "max": int(df["n_genes"].max()),
        "max": 10000,
        "step": 100,
        #        "default": [int(df["n_genes"].min()), int(df["n_genes"].max())],
    },
]
# -------------------------------------------------------------------


def get_layout(config_data):
    layout = dbc.Container(
        html.Div(
            [
                dcc.Store(id="cell-index-key"),  # holds just the key string for the current cell index selection
                dcc.Store(id="color-column-name"),  # holds column name for the current color selection
                dcc.Store(id="dataset-key"),  # holds just the key string for the current dataset
                dcc.Store(id="file-list"),  # holds list of files
                dcc.Store(id="filter-schema-store", data=filter_schema),  # holds the filter schema
                dcc.Store(id="shape-column-name", data=None),  # holds column name for the current shape selection
                html.H1("Single-Cell Transcriptomics Visualization"),
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Button("Rescan", id="rescan", n_clicks=0, color="secondary"),
                            xs=2,
                            lg=1,
                        ),
                        dbc.Col(
                            dcc.Dropdown(
                                id="file-dropdown",
                                options=[],  # filled by callback
                                placeholder=f"Browse {settings.BASE_DIR}…",
                                searchable=True,
                                clearable=False,
                                style={"width": "100%"},
                            ),
                            xs=True,
                        ),
                        dbc.Col(
                            dbc.Checklist(
                                options=[{"label": "Show subfolders", "value": "sub"}],
                                value=["sub"],
                                id="show-subfolders",
                                switch=True,
                            ),
                            xs=4,
                            md=3,
                            xl=2,
                            align="center",
                        ),
                    ],
                    className="gy-2",
                    justify="between",
                ),
                html.Div(id="selected-info", className="mt-3"),
                dcc.Interval(id="init", interval=50, n_intervals=0, max_intervals=1),  # populate once on load
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
                    clearable=False,
                ),
                # Multi-dropdown for gene selection
                html.Div(
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
                    ],
                ),
                html.Div(id="error-message", style={"color": "red"}),
                # Graph container
                html.Div(id="plot-container", style={"display": "flex", "flex-wrap": "wrap"}),
                # Download button and component
                html.Button("Download Plot as SVG", id="download-btn"),
                dcc.Download(id="download-plot"),
                # Button to open filters + active filter summary
                dbc.Button("Filters", id="open-filter-offcanvas", n_clicks=0),
                html.Div(
                    id="active-filters-text",
                    style={"paddingTop": "0.5rem", "fontStyle": "italic"},
                ),
                # Off-canvas drawer holding all filters
                dbc.Offcanvas(
                    id="filter-offcanvas",
                    title="Filters",
                    is_open=False,
                    placement="end",
                    children=html.Div(id="all-filters"),
                    scrollable=True,
                    backdrop=True,
                ),
                # Off-canvas drawer holding all filters
                dbc.Offcanvas(
                    id="filter-left-offcanvas",
                    title="Filters Left",
                    is_open=False,
                    placement="start",
                    children=html.Div([build_left()]),
                    scrollable=True,
                    backdrop=True,
                ),
            ]
        ),
        fluid=True,
    )

    return layout


# -------------------------------------------------------------------
# Helper to build the left-side controls
def build_left():
    html_table_list = [
        dcc.RadioItems(id="r1", options=[{"label": f"R1-{i}", "value": f"R1-{i}"} for i in range(1, 4)], value=None),
        dcc.RadioItems(id="r2", options=[{"label": f"R2-{i}", "value": f"R2-{i}"} for i in range(1, 4)], value=None),
        dcc.RadioItems(id="r3", options=[{"label": f"R3-{i}", "value": f"R3-{i}"} for i in range(1, 4)], value=None),
    ]
    return html.Table(html_table_list, className="table")


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
                        ),
                        dbc.Col(
                            dcc.RadioItems(id=color_id, options=[{"label": "", "value": f["name"]}], value=None),
                            xs=1,
                        ),
                        dbc.Col(
                            dcc.RadioItems(id=shape_id, options=[{"label": "", "value": f["name"]}], value=None),
                            xs=1,
                        ),
                    ]
                ),
            ],
            style={"marginBottom": "1rem"},
        )

    if f["type"] == "numeric_range":
        return html.Div(
            [
                html.Label(f"{f['label']} range"),
                dcc.RangeSlider(
                    id=filter_id,
                    min=f["min"],
                    max=f["max"],
                    step=f["step"],
                    value=f.get("default", [f["min"], f["max"]]),
                    tooltip={"always_visible": False, "placement": "bottom"},
                ),
                html.Div(
                    id={"type": "filter-range-label", "name": f["name"]},
                    style={"fontSize": "0.8rem", "marginTop": "0.25rem"},
                ),
            ],
            style={"marginBottom": "1.5rem"},
        )

    # Fallback (you can add boolean, text, etc. later)
    return html.Div(f"Unsupported filter type: {f['type']}")


# -------------------------------------------------------------------
