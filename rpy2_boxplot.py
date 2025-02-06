
import pandas as pd

host = "0.0.0.0"
port = 61040

rds_file = "testdata/20220818_brain_10x-test_rna-seurat.rds"
met_file = "testdata/seurat_metadata.csv"

# Load the RDS file
from rpy2.robjects import r
from rpy2.robjects import pandas2ri
try:
	r_obj = r['readRDS'](rds_file)
	r_dgC = r['LayerData'](r_obj, assay = "SCT", layer = "counts")
except Exception as e:
	print(e)
	print("Unable to read RDS file")
r_df  = r['as.data.frame'](r_dgC)
pandas2ri.activate()
df = pandas2ri.rpy2py(r_df).transpose()
#df = pd.read_csv(csv_file, index_col="Unnamed: 0", usecols=lambda x: x not in ["RowNames"]).transpose()
mygenes = df.columns
df = df.reset_index().melt(id_vars=["index"], value_vars=df.columns, var_name="Gene", value_name="Counts").set_index('index')

meta = pd.read_csv(met_file, index_col="Unnamed: 0", usecols=["Unnamed: 0", "condition_1", "condition_2"])
df = df.join(meta, on='index', how='left')

#import rpy2.robjects as ro
#with (ro.default_converter + pandas2ri.converter).context():
#  df = ro.conversion.get_conversion().rpy2py(r_df)

import dash
from dash import dcc, html, Output, Input
import plotly.express as px

# Prep the Dash App
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Box and Whiskers Plot Example"),

    # Selecting which metadata to show
    dcc.Checklist(
        options=meta.columns,
        inline=True,
        value=[meta.columns[0]],
        id="box-checklist",
    ),

    # Dropdown for selecting the variable
    dcc.Dropdown(
        id="box-dropdown",
        options=[
            {"label": col, "value": col} for col in mygenes
        ],
        multi=True,  # Enable multiple selection
        value=mygenes[0:10],  # Default value
        placeholder="Select a column to plot"
    ),

    # The Graph
    dcc.Graph(id="box-plot")
])

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

    stacked_df = df.loc[df['Gene'].isin(selected_columns)]
    color = stacked_df[color_context].agg('/'.join, axis=1)

    # Create the box plot with a logarithmic y-axis
    fig = px.box(
        stacked_df,
        x="Gene",
        y="Counts",
        color=color,
        title=f"Box and Whiskers Plot for {selected_columns}",
        log_y=True  # Logarithmic scale
    )
    return fig

if __name__ == "__main__":
    app.run_server(port=port, host=host, debug=True)


