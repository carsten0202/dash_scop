import numpy as np
import pandas as pd
import plotly.express as px
from dash import Input, Output, dcc, html


# Placeholder function to generate example data
def generate_data(plot_type):
    if plot_type == "boxplot":
        df = pd.DataFrame(
            {
                "Gene": np.random.choice(["GeneA", "GeneB", "GeneC"], 100),
                "Expression": np.random.randn(100),
            }
        )
        return px.box(df, x="Gene", y="Expression", title="Boxplot of Gene Expression")

    elif plot_type == "umap":
        df = pd.DataFrame(
            {
                "UMAP1": np.random.randn(100),
                "UMAP2": np.random.randn(100),
                "Cluster": np.random.choice(["Cluster1", "Cluster2", "Cluster3"], 100),
            }
        )
        return px.scatter(df, x="UMAP1", y="UMAP2", color="Cluster", title="UMAP Scatterplot")

    elif plot_type == "violin":
        df = pd.DataFrame(
            {
                "Gene": np.random.choice(["GeneA", "GeneB", "GeneC"], 100),
                "Expression": np.random.randn(100),
            }
        )
        return px.violin(
            df, x="Gene", y="Expression", box=True, points="all", title="Violin Plot of Gene Expression"
        )

    elif plot_type == "heatmap":
        heatmap_data = np.random.rand(10, 10)
        return px.imshow(heatmap_data, color_continuous_scale="Viridis", title="Gene Expression Heatmap")

    return px.scatter()


# def register_callbacks(app):
#     @app.callback(Output("plot-output", "figure"), Input("plot-selector", "value"))
#     def update_plot(plot_type):
#         return generate_data(plot_type)


# Placeholder function to simulate single-cell transcriptomics data
def generate_example_data():
    np.random.seed(42)
    df = pd.DataFrame(
        {
            "Gene": np.random.choice(["GeneA", "GeneB", "GeneC", "GeneD"], 500),
            "Expression": np.random.randn(500),
            "UMAP1": np.random.randn(500),
            "UMAP2": np.random.randn(500),
            "Cluster": np.random.choice(["Cluster1", "Cluster2", "Cluster3"], 500),
            "CellType": np.random.choice(["T Cell", "B Cell", "Macrophage"], 500),
        }
    )
    return df


df = generate_example_data()


def register_callbacks(app):
    @app.callback(
        Output("gene-selector", "options"),
        Output("cell-type-filter", "options"),
        Input("plot-selector", "value"),
    )
    def update_gene_and_celltype_options(plot_type):
        gene_options = [{"label": gene, "value": gene} for gene in df["Gene"].unique()]
        cell_type_options = [{"label": cell, "value": cell} for cell in df["CellType"].unique()]
        return gene_options, cell_type_options

    @app.callback(
        Output("plot-container", "children"),
        Input("plot-selector", "value"),
        Input("gene-selector", "value"),
        Input("cell-type-filter", "value"),
    )
    def update_plots(plot_type, selected_genes, selected_cell_types):
        if selected_genes is None or len(selected_genes) == 0:
            selected_genes = df["Gene"].unique()[:1]  # Default to one gene
        if selected_cell_types is None or len(selected_cell_types) == 0:
            selected_cell_types = df["CellType"].unique()  # No filter

        filtered_df = df[df["Gene"].isin(selected_genes) & df["CellType"].isin(selected_cell_types)]

        plot_figures = []

        if plot_type == "boxplot":
            for gene in selected_genes:
                fig = px.box(
                    filtered_df[filtered_df["Gene"] == gene],
                    x="CellType",
                    y="Expression",
                    title=f"Boxplot for {gene}",
                )
                plot_figures.append(
                    html.Div(dcc.Graph(figure=fig), style={"width": "48%", "display": "inline-block"})
                )

        elif plot_type == "umap":
            fig = px.scatter(filtered_df, x="UMAP1", y="UMAP2", color="Cluster", title="UMAP Scatterplot")
            plot_figures.append(html.Div(dcc.Graph(figure=fig), style={"width": "100%"}))

        elif plot_type == "violin":
            fig = px.violin(
                filtered_df,
                x="Gene",
                y="Expression",
                color="CellType",
                box=True,
                points="all",
                title="Violin Plot",
            )
            plot_figures.append(html.Div(dcc.Graph(figure=fig), style={"width": "100%"}))

        elif plot_type == "heatmap":
            heatmap_data = np.random.rand(10, len(selected_genes))
            fig = px.imshow(heatmap_data, color_continuous_scale="Viridis", title="Gene Expression Heatmap")
            plot_figures.append(html.Div(dcc.Graph(figure=fig), style={"width": "100%"}))

        return plot_figures
