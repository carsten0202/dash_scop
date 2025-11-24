import dash_bootstrap_components as dbc
from dash import dcc, html

import settings

# This is what, in your app, you'd derive from the Seurat metadata
filter_schema = [
    {
        "name": "cell_type",
        "label": "Cell type",
        "type": "categorical",
        "values": [],  # to be filled dynamically
        #        "values": sorted(df["cell_type"].unique()),
        "default": [],  # empty means "no filter"
    },
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
    {
        "name": "pct_mito",
        "label": "Mito percent",
        "type": "numeric_range",
        #        "min": int(df["pct_mito"].min()),
        "min": 0,
        #        "max": int(df["pct_mito"].max()),
        "max": 100,
        "step": 1,
        #        "default": [int(df["pct_mito"].min()), int(df["pct_mito"].max())],
    },
]
# -------------------------------------------------------------------


def get_layout(config_data):
    layout = dbc.Container(
        html.Div(
            [
                dcc.Store(id="file-list"),  # holds list of files
                dcc.Store(id="filter-schema-store", data=filter_schema),  # holds the filter schema
                dcc.Store(id="dataset-key"),  # holds just the key string
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
            ]
        ),
        fluid=True,
    )

    return layout
