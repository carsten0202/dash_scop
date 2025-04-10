import dash
import pandas as pd
import plotly.express as px
from dash import Input, Output, dcc, html

host = "0.0.0.0"
port = 61040

csv_file = "testdata/20220818_brain_10x-test_rna-seurat.csv"
met_file = "testdata/seurat_metadata.csv"

df = pd.read_csv(csv_file, index_col="Unnamed: 0", usecols=lambda x: x not in ["RowNames"]).transpose()
mygenes = df.columns
df = (
    df.reset_index()
    .melt(
        id_vars=["index"],
        value_vars=df.columns,
        var_name="Gene",
        value_name="Counts",
    )
    .set_index("index")
)
meta = pd.read_csv(met_file, index_col="Unnamed: 0", usecols=["Unnamed: 0", "condition_1", "condition_2"])
df = df.join(meta, on="index", how="left")

# Prep the Dash App
app = dash.Dash(__name__)

app.layout = html.Div(
    [
        html.H1("Box and Whiskers Plot Example"),
        # Selecting which metadata to show
        dcc.Checklist(
            id="box-checklist",
            options=meta.columns,
            inline=True,
            value=[meta.columns[0]],
        ),
        # Dropdown for selecting the variable
        dcc.Dropdown(
            id="box-dropdown",
            options=[{"label": col, "value": col} for col in mygenes],
            multi=True,  # Enable multiple selection
            value=mygenes[0:10],  # Default value
            placeholder="Select a column to plot",
        ),
        # The Graph
        dcc.Graph(id="box-plot"),
    ]
)


# Callback to update the plot based on the dropdown selection
@app.callback(
    Output(component_id="box-plot", component_property="figure"),
    Input(component_id="box-dropdown", component_property="value"),
    Input(component_id="box-checklist", component_property="value"),
)
def update_plot(selected_columns, color_context):
    # If no columns are selected, return an empty figure
    if not selected_columns:
        return px.box(title="No data selected")

    stacked_df = df.loc[df["Gene"].isin(selected_columns)]
    color = stacked_df[color_context].agg("/".join, axis=1)

    # Create the box plot with a logarithmic y-axis
    fig = px.box(
        stacked_df,
        x="Gene",
        y="Counts",
        color=color,
        title=f"Box and Whiskers Plot for {selected_columns}",
        log_y=True,  # Logarithmic scale
    )
    return fig


if __name__ == "__main__":
    app.run_server(port=port, host=host, debug=True)
