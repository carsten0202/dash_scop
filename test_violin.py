import numpy as np
import pandas as pd
import plotly.express as px
from dash import Dash, Input, Output, dcc, html

Options = {
    "host": "0.0.0.0",
    "port": 61020,
    "x": "Cell Types",
    "y": "Expression Counts",
    "title": "Violin Plot Example",
}

rds_file = "testdata/20220818_brain_10x-test_rna-seurat.rds"
csv_file = "testdata/20220818_brain_10x-test_rna-seurat.csv"

df = pd.read_csv(csv_file, index_col="Unnamed: 0", usecols=lambda x: x not in ["RowNames"])
df = df.reset_index().melt(
    id_vars=["index"], value_vars=df.columns, var_name=Options["x"], value_name=Options["y"]
)
with np.errstate(divide="ignore"):
    df[Options["y"]] = np.log10(df[Options["y"]])  # Logarithmic scale


# Dash App
app = Dash(__name__)

categories = df[Options["x"]].unique()
app.layout = html.Div(
    [
        html.H1("Violin Plot in Dash & Plotly"),
        # Dropdown for selecting variables to plot
        dcc.Dropdown(
            id="violin-dropdown",
            multi=True,  # Enable multiple selection
            options=[{"label": col, "value": col} for col in categories],
            placeholder="Select a column to plot",
            value=categories[0:10],  # Default value
        ),
        # The Graph
        dcc.Graph(
            id="violin-plot",
        ),
    ]
)


@app.callback(
    Output(component_id="violin-plot", component_property="figure"),
    Input(component_id="violin-dropdown", component_property="value"),
)
def update_plot(selected_columns):
    # If no columns are selected, return an empty figure
    if not selected_columns:
        return px.violin(title="No data selected")

    stacked_df = df.loc[df[Options["x"]].isin(selected_columns)]
    color = stacked_df[Options["x"]]

    # Create the box plot with a logarithmic y-axis
    fig = px.violin(
        stacked_df,
        color=color,
        points="all",
        title=Options["title"],
        x=Options["x"],
        y=Options["y"],
    )
    return fig


# Run Server
if __name__ == "__main__":
    app.run_server(host=Options["host"], port=Options["port"], debug=True)
