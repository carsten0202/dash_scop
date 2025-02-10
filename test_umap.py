
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Output, Input

host = "0.0.0.0"
port = 61010

csv_file = "testdata/umap_coordinates.csv"
met_file = "testdata/seurat_metadata.csv"

df = pd.read_csv(csv_file, index_col="Unnamed: 0", usecols=['Unnamed: 0', 'UMAP_1', 'UMAP_2'])
meta = pd.read_csv(met_file, index_col="Unnamed: 0", usecols=['Unnamed: 0', 'condition_1','condition_2'])
df = df.join(meta, how='left')
df['variable'] = df['condition_1'].astype(str) + "/" + df['condition_2']

context = df['variable'].unique()
options = [{'label': con, 'value': con} for con in context]

app = Dash(__name__)

app.layout = html.Div(
    [
        dcc.Checklist(
            id="checklist",
            options=options,
            inline=True,
            value=context,
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
        df[df["variable"].isin(values)],
        x="UMAP_1",
        y="UMAP_2",
        color="variable",
    )
    return fig


if __name__ == "__main__":
    app.run_server(host=host, port=port, debug=True)
