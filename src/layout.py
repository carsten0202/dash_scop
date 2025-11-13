import dash_bootstrap_components as dbc
from dash import dcc, html

import settings


def get_layout(config_data):
    layout = dbc.Container(
        html.Div(
            [
                html.H1("Single-Cell Transcriptomics Visualization"),
                dbc.Row(
                    [
                        dbc.Col(
                            dcc.Dropdown(
                                id="file-dropdown",
                                options=[],  # filled by callback
                                placeholder=f"Browse {settings.BASE_DIR}…",
                                searchable=True,
                                clearable=False,
                                style={"width": "100%"},
                            ),
                            md=8,
                        ),
                        dbc.Col(
                            dbc.Button("Rescan", id="rescan", n_clicks=0, color="secondary"),
                            md=2,
                        ),
                        dbc.Col(
                            dbc.Checklist(
                                options=[{"label": "Show subfolders", "value": "sub"}],
                                value=["sub"],
                                id="show-subfolders",
                                switch=True,
                            ),
                            md=2,
                        ),
                    ],
                    className="gy-2",
                ),
                html.Div(id="selected-info", className="mt-3"),
                dcc.Store(id="file-list"),  # holds list of files
                dcc.Store(id="dataset-key"),  # holds just the key string
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
                # Checklist for cell type filtering
                html.Label("Filter by cell type:"),
                dcc.Checklist(
                    id="cell-type-filter",
                    options=[],  # Populated dynamically
                    inline=True,
                ),
                html.Div(id="error-message", style={"color": "red"}),
                # Graph container
                html.Div(id="plot-container", style={"display": "flex", "flex-wrap": "wrap"}),
                # Download button and component
                html.Button("Download Plot as SVG", id="download-btn"),
                dcc.Download(id="download-plot"),
            ]
        ),
        fluid=True,
    )
    return layout
