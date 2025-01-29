import pandas as pd

host = "0.0.0.0"
port = 61020

rds_file = "testdata/20220818_brain_10x-test_rna-seurat.rds"
csv_file = "testdata/20220818_brain_10x-test_rna-seurat.csv"

df = pd.read_csv(csv_file, index_col="Unnamed: 0", usecols=range(26)).transpose()
mygenes = df.columns
df = df.reset_index().melt(id_vars=["index"], value_vars=df.columns, var_name="Gene", value_name="Counts")





import dash
from dash import dcc, html
import plotly.express as px
import numpy as np

# Sample Data
np.random.seed(42)
df = pd.DataFrame({
    "Category": np.random.choice(["A", "B", "C"], 300),
    "Value": np.concatenate([
        np.random.normal(50, 10, 100),
        np.random.normal(70, 15, 100),
        np.random.normal(60, 12, 100)
    ])
})

print(df)

# Create Violin Plot
fig = px.violin(df, x="Category", y="Value", box=True, points="all", title="Violin Plot Example")

# Dash App
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Violin Plot in Dash & Plotly"),
    dcc.Graph(figure=fig)
])

# Run Server
if __name__ == '__main__':
    app.run_server(host=host, port=port, debug=True)


