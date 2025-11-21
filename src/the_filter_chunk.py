import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html
from dash.dependencies import ALL, Input, Output, State

# -------------------------------------------------------------------
# Dummy data + filter schema (replace with your Seurat/R schema later)
# -------------------------------------------------------------------

# Example "cell-level" data
df = pd.DataFrame(
    {
        "cell_type": ["T cell", "B cell", "Monocyte", "T cell", "B cell", "Monocyte"] * 50,
        "batch": ["A", "B", "C"] * 100,
        "sample_id": ["S1", "S2"] * 150,
        "n_genes": [500, 800, 1200, 2000, 300, 1000] * 50,
        "pct_mito": [5, 10, 15, 20, 8, 12] * 50,
    }
)

# This is what, in your app, you'd derive from the Seurat metadata
filter_schema = [
    {
        "name": "cell_type",
        "label": "Cell type",
        "type": "categorical",
        "values": sorted(df["cell_type"].unique()),
        "default": [],  # empty means "no filter"
    },
    {
        "name": "batch",
        "label": "Batch",
        "type": "categorical",
        "values": sorted(df["batch"].unique()),
        "default": [],
    },
    {
        "name": "sample_id",
        "label": "Sample",
        "type": "categorical",
        "values": sorted(df["sample_id"].unique()),
        "default": [],
    },
    {
        "name": "n_genes",
        "label": "Number of genes",
        "type": "numeric_range",
        "min": int(df["n_genes"].min()),
        "max": int(df["n_genes"].max()),
        "step": 100,
        "default": [int(df["n_genes"].min()), int(df["n_genes"].max())],
    },
    {
        "name": "pct_mito",
        "label": "Mito percent",
        "type": "numeric_range",
        "min": int(df["pct_mito"].min()),
        "max": int(df["pct_mito"].max()),
        "step": 1,
        "default": [int(df["pct_mito"].min()), int(df["pct_mito"].max())],
    },
]

# -------------------------------------------------------------------
# Helper to build a control for a single filter definition
# -------------------------------------------------------------------


def make_filter_component(f):
    filter_id = {"type": "filter-control", "name": f["name"]}

    if f["type"] == "categorical":
        return html.Div(
            [
                html.Label(f["label"]),
                dcc.Dropdown(
                    id=filter_id,
                    options=[{"label": v, "value": v} for v in f["values"]],
                    multi=True,
                    value=f.get("default", []),
                    placeholder=f"Select {f['label'].lower()}",
                ),
            ],
            style={"marginBottom": "1rem"},
        )

    if f["type"] == "numeric_range":
        return html.Div(
            [
                html.Label(f"{f['label']} range"),
                dcc.RangeSlider(
                    id=filter_id,
                    min=f["min"],
                    max=f["max"],
                    step=f["step"],
                    value=f.get("default", [f["min"], f["max"]]),
                    tooltip={"always_visible": False, "placement": "bottom"},
                ),
                html.Div(
                    id={"type": "filter-range-label", "name": f["name"]},
                    style={"fontSize": "0.8rem", "marginTop": "0.25rem"},
                ),
            ],
            style={"marginBottom": "1.5rem"},
        )

    # Fallback (you can add boolean, text, etc. later)
    return html.Div(f"Unsupported filter type: {f['type']}")


# -------------------------------------------------------------------
# App layout
# -------------------------------------------------------------------

external_stylesheets = [dbc.themes.BOOTSTRAP]

app: Dash = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = dbc.Container(
    [
        # Store for the schema – in your app this could be populated by a callback
        dcc.Store(id="filter-schema-store", data=filter_schema),
        html.H2("Dynamic filters demo"),
        # Top bar: button to open filters + active filter summary
        dbc.Row(
            [
                dbc.Col(
                    dbc.Button("Filters", id="open-filter-offcanvas", n_clicks=0),
                    width="auto",
                ),
                dbc.Col(
                    html.Div(
                        id="active-filters-text",
                        style={"paddingTop": "0.5rem", "fontStyle": "italic"},
                    ),
                ),
            ],
            align="center",
            className="mb-3",
        ),
        # Main figure
        dcc.Graph(id="main-plot"),
        # Off-canvas drawer holding all filters
        dbc.Offcanvas(
            id="filter-offcanvas",
            title="Filters",
            is_open=False,
            placement="end",
            children=html.Div(id="all-filters"),
            scrollable=True,
            backdrop=True,
        ),
    ],
    fluid=True,
)


# -------------------------------------------------------------------
# Callback: build all filter components dynamically from schema
# -------------------------------------------------------------------


@app.callback(
    Output("all-filters", "children"),
    Input("filter-schema-store", "data"),
)
def build_filter_components(schema):
    if not schema:
        return html.Div("No filters defined.")
    return [make_filter_component(f) for f in schema]


# -------------------------------------------------------------------
# Callback: update numeric range labels (purely cosmetic)
# -------------------------------------------------------------------


@app.callback(
    Output({"type": "filter-range-label", "name": ALL}, "children"),
    Input({"type": "filter-control", "name": ALL}, "value"),
    State({"type": "filter-control", "name": ALL}, "id"),
)
def update_range_labels(values, ids):
    labels = []
    for v, id_ in zip(values, ids):
        # Only handle numeric_range filters -> they will send a list [min, max]
        if isinstance(v, (list, tuple)) and len(v) == 2:
            labels.append(f"{id_['name']}: {v[0]} – {v[1]}")
        else:
            labels.append("")
    return labels


# -------------------------------------------------------------------
# Callback: toggle filters drawer
# -------------------------------------------------------------------


@app.callback(
    Output("filter-offcanvas", "is_open"),
    Input("open-filter-offcanvas", "n_clicks"),
    State("filter-offcanvas", "is_open"),
)
def toggle_offcanvas(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open


# -------------------------------------------------------------------
# Callback: apply all filters and update the plot
# -------------------------------------------------------------------


@app.callback(
    Output("main-plot", "figure"),
    Output("active-filters-text", "children"),
    Input({"type": "filter-control", "name": ALL}, "value"),
    State({"type": "filter-control", "name": ALL}, "id"),
    State("filter-schema-store", "data"),
)
def update_plot(values, ids, schema):
    # Map schema by name for quick lookup
    schema_by_name = {f["name"]: f for f in schema}

    dff = df.copy()
    active_descriptions = []

    for val, id_ in zip(values, ids):
        name = id_["name"]
        f = schema_by_name.get(name)
        if not f:
            continue

        if f["type"] == "categorical":
            if val:  # list of categories
                dff = dff[dff[name].isin(val)]
                active_descriptions.append(f"{f['label']}: {', '.join(map(str, val))}")

        elif f["type"] == "numeric_range":
            if isinstance(val, (list, tuple)) and len(val) == 2:
                low, high = val
                dff = dff[(dff[name] >= low) & (dff[name] <= high)]
                active_descriptions.append(f"{f['label']}: {low} – {high}")

        # You can extend with more types here

    # Simple example plot – adapt to your UMAP, boxplots, etc.
    if dff.empty:
        fig = px.scatter(title="No data after filtering")
    else:
        fig = px.scatter(
            dff,
            x="n_genes",
            y="pct_mito",
            color="cell_type",
            hover_data=["batch", "sample_id"],
            title="Example plot: n_genes vs pct_mito",
        )

    if active_descriptions:
        summary = "Active filters: " + " | ".join(active_descriptions)
    else:
        summary = "No filters applied"

    return fig, summary


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

if __name__ == "__main__":
    app.run_server(debug=True)
