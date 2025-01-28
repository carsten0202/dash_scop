
import pandas as pd

host = "0.0.0.0"
port = 61040

rds_file = "testdata/20220818_brain_10x-test_rna-seurat.rds"
csv_file = "testdata/20220818_brain_10x-test_rna-seurat.csv"

df = pd.read_csv(csv_file, index_col="Unnamed: 0", usecols=range(26)).transpose()
mygenes = df.columns
df = df.reset_index().melt(id_vars=["index"], value_vars=df.columns, var_name="Gene", value_name="Counts")


#import rpy2.robjects as ro
#from rpy2.robjects import r

# Load the RDS file
# try:
# 	r_object = ro.r['readRDS'](rds_file)
	# If the R object is a data frame, you can convert it to a pandas DataFrame
#	if isinstance(r_object, ro.vectors.DataFrame):
#		df = pd.DataFrame({col: list(r_object[col]) for col in r_object.names})
# except:
# 	print("Unable to read RDS file")

import dash
from dash import dcc, html, callback, Output, Input
import plotly.express as px


# Prep the Dash App
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Box and Whiskers Plot Example"),
    # Dropdown for selecting the variable
    dcc.Dropdown(
        id="variable-dropdown",
        options=[
            {"label": col, "value": col} for col in mygenes
        ],
        multi=True,  # Enable multiple selection
        value=mygenes[0:3],  # Default value
        placeholder="Select a column to plot"
    ),
    dcc.Graph(id="box-plot")
])

# Callback to update the plot based on the dropdown selection
@app.callback(
    Output(component_id="box-plot", component_property="figure"),
    Input(component_id="variable-dropdown", component_property="value")
)
def update_plot(selected_columns):
    # If no columns are selected, return an empty figure
    if not selected_columns: 
        return px.box(title="No data selected")

    stacked_df = df.loc[df['Gene'].isin(selected_columns)]

    # Create the box plot with a logarithmic y-axis
    fig = px.box(
        stacked_df,
        x="Gene",
        y="Counts",
        title=f"Box and Whiskers Plot for {selected_columns}",
        log_y=True  # Logarithmic scale
    )
    return fig

if __name__ == "__main__":
    app.run_server(port=port, host=host, debug=True)


