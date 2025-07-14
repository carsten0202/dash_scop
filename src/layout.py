from dash import dcc, html

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
        html.Div(
            id="gene-selector-container",
            children=[
                html.Label("Select gene(s):", htmlFor="gene-selector"),
                dcc.Dropdown(
                    id="gene-selector",
                    options=[],  # Populated dynamically
                    multi=True,
                    placeholder="Select genes to display...",
					value=[],
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
)
