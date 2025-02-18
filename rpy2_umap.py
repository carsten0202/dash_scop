import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html
from rpy2.robjects import pandas2ri, r

host = "0.0.0.0"
port = 61010

rds_file = "testdata/20220818_brain_10x-test_rna-seurat.rds"
met_file = "testdata/seurat_metadata.csv"

# Load the RDS file
pandas2ri.activate()
try:
    robj = r["readRDS"](rds_file)
    umap = robj.slots["reductions"].rx2("umap")
#    emb = r['Embeddings'](robj, reduction="umap")
except Exception as e:
    print(e)
    print("Unable to read RDS file")


meta = pd.read_csv(met_file, index_col="Unnamed: 0")
df = pd.DataFrame(umap.slots["cell.embeddings"], index=r["rownames"](umap), columns=r["colnames"](umap))
df = df.join(meta[["condition_1", "condition_2"]], how="left")
df["variable"] = df["condition_1"].astype(str) + "/" + df["condition_2"]

context = df["variable"].unique()
options = [{"label": con, "value": con} for con in context]

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
