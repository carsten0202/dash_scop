
import rpy2.robjects as ro
from rpy2.robjects import r
#import pandas as pd

# Load the RDS file
# try:
# 	rds_file = "testdata/20220818_brain_10x-test_rna-seurat.rds"
# 	r_object = ro.r['readRDS'](rds_file)
	# If the R object is a data frame, you can convert it to a pandas DataFrame
#	if isinstance(r_object, ro.vectors.DataFrame):
#		df = pd.DataFrame({col: list(r_object[col]) for col in r_object.names})
# except:
# 	print("Unable to read RDS file")

testgenes = ['Lypla1', 'Tcea1', 'Gm16041', 'Atp6v1h', 'Oprk1', 'Rb1cc1', 'Alkal1', 'Arl14ep', 'Fshb', 'Gm13912']

import pandas as pd
df = pd.read_csv("testdata/20220818_brain_10x-test_rna-seurat.csv", index_col="RowNames", usecols = lambda x: x not in ["Unnamed: 0"]).transpose()

import dash
from dash import dcc, html, callback, Output, Input
import plotly.express as px

# Example DataFrame
# df = pd.DataFrame({
#     "Gene": ["A", "A", "A", "B", "B", "B", "C", "C", "C"],
#     "Counts": [10, 12, 11, 15, 14, 16, 20, 21, 19]
# })

df = df.reset_index().melt(id_vars=["index"], value_vars=testgenes, var_name="Gene", value_name="Counts")

print(testgenes[0:3])
print(df.loc[df['Gene'].isin(testgenes[0:3])])

# Create the box plot
# fig = px.box(df, x="Gene", y="Counts", title="Box and Whiskers Plot", log_y=True)

# Dash App
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Box and Whiskers Plot Example"),
    # Dropdown for selecting the variable
    dcc.Dropdown(
        id="variable-dropdown",
        options=[
            {"label": col, "value": col} for col in testgenes
        ],
        multi=True,  # Enable multiple selection
        value=testgenes,  # Default value
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
    app.run_server(debug=True)


