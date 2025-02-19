from dash import dcc, html

# Layout for the Dash app
layout = html.Div(
    [
        html.H1("Single-Cell Transcriptomics Visualization"),
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
        html.Label("Select genes:"),
        dcc.Dropdown(
            id="gene-selector",
            options=[],  # Will be populated dynamically
            multi=True,
            placeholder="Select genes to display...",
        ),
        # Checklist for cell type filtering
        html.Label("Filter by cell type:"),
        dcc.Checklist(
            id="cell-type-filter",
            options=[],  # Will be populated dynamically
            inline=True,
        ),
        # Graph container for plots (allowing side-by-side)
        html.Div(id="plot-container", style={"display": "flex", "flex-wrap": "wrap"}),
    ]
)
