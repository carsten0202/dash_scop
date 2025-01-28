
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Output, Input

host = "0.0.0.0"
port = 61010

rds_file = "testdata/20220818_brain_10x-test_rna-seurat.rds"
csv_file = "testdata/umap_coordinates.csv"

df = pd.read_csv(csv_file, index_col="Unnamed: 0")
df[['column1', 'species']] = df.index.to_series().str.split('_', expand=True)
species = df["species"].unique().tolist()
options = [{"label": specie.capitalize(), "value": specie} for specie in species]

app = Dash(__name__)

app.layout = html.Div(
    [
        dcc.Checklist(
            options=options,
            inline=True,
            value=species,
            id="checklist",
        ),
        dcc.Graph(id="scatter"),
    ]
)


@app.callback(
    Output("scatter", "figure"),
    Input("checklist", "value"),
)
def update_figure(values):
    fig = px.scatter(
        df[df["species"].isin(values)],
        x="UMAP_1",
        y="UMAP_2",
        color="species",
    )
    return fig


if __name__ == "__main__":
    app.run_server(host=host, port=port, debug=True)
