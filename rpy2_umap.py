
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Output, Input

host = "0.0.0.0"
port = 61010

rds_file = "testdata/20220818_brain_10x-test_rna-seurat.rds"
met_file = "testdata/seurat_metadata.csv"

# Load the RDS file
from rpy2.robjects import r, pandas2ri
pandas2ri.activate()
try:
	r_obj = r['readRDS'](rds_file)
#	r_dgC = r['LayerData'](r_obj, assay = "SCT", layer = "counts")
except Exception as e:
	print(e)
	print("Unable to read RDS file")

r_df = x@reductions$umap@cell.embeddings

import scanpy as sc
# Load the converted h5ad file
adata = sc.read_h5ad("testdata/seurat_data.h5ad")
df = pd.DataFrame(adata.obsm['X_umap'], adata.obs.index, columns=['UMAP_1', 'UMAP_2'])
print(adata.obs)
print(adata.obs['nCount_RNA'])

meta = pd.read_csv(met_file, index_col="Unnamed: 0")
df = df.join(meta[['condition_1','condition_2']], how='left')
df['variable'] = df['condition_1'].astype(str) + "/" + df['condition_2']

context = df['variable'].unique()
options = [{'label': con, 'value': con} for con in context]

app = Dash(__name__)

app.layout = html.Div(
    [
        dcc.Checklist(
            options=options,
            inline=True,
            value=context,
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
        df[df["variable"].isin(values)],
        x="UMAP_1",
        y="UMAP_2",
        color="variable",
    )
    return fig


if __name__ == "__main__":
    app.run_server(host=host, port=port, debug=True)
