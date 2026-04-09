import base64
import json
import os
from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import rpy2.robjects as ro
import yaml
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter

import settings


# -------------------------------------------------------------------
# Underlying function to fetch expression subset for given genes and cells
def _expression_subset(
    seurat_handle: str,
    genes: list[str] | None = None,
    cells: list[str] | None = None,
):
    with localconverter(ro.default_converter + pandas2ri.converter):
        r_genes = ro.StrVector(genes) if genes else ro.NULL
        r_cells = ro.StrVector(cells) if cells else ro.NULL
        res = ro.r["get_expression_subset_matrix"](seurat_handle, r_genes, r_cells)  # type: ignore

    values = res[0]
    rownames = list(res[1])
    colnames = list(res[2])

    return (values, rownames, colnames)
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# Helper to fetch expression subset for given genes and cells
def fetch_expression_subset(
    seurat_handle: str,
    genes: list[str] | None = None,
    cells: list[str] | None = None,
) -> pd.DataFrame:
    (values, rownames, colnames) = _expression_subset(seurat_handle, genes, cells)

    return pd.DataFrame(values, index=rownames, columns=colnames)
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper to fetch expression subset for given genes and cells, returning z-scores
def fetch_expression_subset_zscores(
    seurat_handle: str,
    genes: list[str] | None = None,
    cells: list[str] | None = None,
) -> pd.DataFrame:
    (values, rownames, colnames) = _expression_subset(seurat_handle, genes, cells)

    # Calculat z-scores across cells for each gene using numpy for efficiency
    means = values.mean(axis=1, keepdims=True)
    stds = values.std(axis=1, keepdims=True)
    stds[stds == 0] = 1.0
    values = (values - means) / stds

    return pd.DataFrame(values, index=rownames, columns=colnames)
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper to build the filter schema from the metadata
def filter_from_metadata(metadata_df):
    filter_schema = []
    for series in [metadata_df[c] for c in metadata_df.columns]:  # Loop over series in metadata data frame
        if series.dtype in ["category"]: # Note that some types convert to category in data_loader.py
            f = {
                "name": series.name,
                "label": series.name,
                "type": "categorical",
                "values": sorted(series.unique()),
                "default": [],  # empty means "no filter selected"
            }
        elif series.dtype in ["int64", "float64", "int32", "float32"]:
            f = {
                "name": series.name,
                "label": series.name,
                "type": "numeric_range",
                "min": int(series.min()),
                "max": int(series.max()),
                "step": 100,
                "default": [],
            }
        else:
            continue  # Skip unsupported types
        filter_schema.append(f)
    return filter_schema
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper to generate a boxplot figure
def generate_boxplot(expression_df, cell_metadata, gene, shape_column, gene_label=None):
    """Generate a boxplot figure lazily from expression data and metadata."""
    display_gene = gene_label or gene
    plot_df = expression_df.transpose().copy()
    plot_df.index.name = "Cell"
    plot_df = plot_df.reset_index()

    if shape_column and shape_column in cell_metadata.columns:
        plot_df = plot_df.merge(cell_metadata[[shape_column]], left_on="Cell", right_index=True, how="left")

    if shape_column and shape_column in plot_df.columns:
        fig_df = plot_df[["Cell", shape_column, gene]].rename(columns={gene: display_gene})
        fig = px.box(
            fig_df,
            x=shape_column,
            y=display_gene,
            labels={shape_column: shape_column, display_gene: "Expression"},
            title=f"Boxplot for {display_gene}",
        )
    else:
        fig_df = plot_df[["Cell", gene]].rename(columns={gene: display_gene})
        fig = px.box(
            fig_df,
            y=display_gene,
            labels={display_gene: "Expression"},
            title=f"Boxplot for {display_gene}",
        )
    return fig
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper to generate a heatmap figure
def generate_heatmap(heatmap_df, gene_labels=None):
    display_df = heatmap_df.rename(index=lambda gene: gene_labels.get(gene, gene) if gene_labels else gene)

    heatmap_figure = px.imshow(
        display_df,
        color_continuous_scale="Viridis",
        title="Gene Expression Heatmap",
        x=display_df.columns,  # columns
        y=display_df.index.tolist(), # rows
        aspect="auto",
        # aspect="equal",
        labels=dict(x="Barcodes", y="Genes", color="Expr"),  # axis titles & color-bar
    )

    # Don't show labels if there's too many
    if len(display_df.columns) > settings.max_ticks_y:
        heatmap_figure.update_yaxes(showticklabels=False)
    if len(display_df.index.tolist()) > settings.max_ticks_x:
        heatmap_figure.update_xaxes(showticklabels=False)

    return heatmap_figure
# -------------------------------------------------------------------

# -------------------------------------------------------------------
def generate_umap(umap_df, color, shape):
    """Generate a UMAP scatterplot figure."""
    umap_figure = px.scatter(
        umap_df,
        x="UMAP_1",
        y="UMAP_2",
        color=color,
        symbol=shape,
        title="UMAP Scatterplot",
    )
    return umap_figure
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper to generate a violin plot figure
def generate_violin(violin_df, genes, cell_metadata, shape_column, gene_labels=None):
    """Generate a violin plot figure."""

    if not genes:
        raise ValueError("For Violin plots please select one or more features.")
    elif len(genes) > settings.max_features:
        raise ValueError(f"For Violin plots please select no more than {settings.max_features} features.")

    plot_df = violin_df.transpose().copy()
    plot_df.index.name = "Cell"
    plot_df = plot_df.reset_index()
    if gene_labels:
        plot_df = plot_df.rename(columns={gene: gene_labels.get(gene, gene) for gene in genes})

    if shape_column and shape_column in cell_metadata.columns:
        plot_df = plot_df.merge(cell_metadata[[shape_column]], left_on="Cell", right_index=True, how="left")

    id_vars = ["Cell"]
    if shape_column and shape_column in plot_df.columns:
        id_vars.append(shape_column)

    long_df = plot_df.melt(id_vars=id_vars, var_name="Gene", value_name="Expression")

    violin_figure = px.violin(
        long_df,
        x="Gene",
        y="Expression",
        color=shape_column if shape_column and shape_column in long_df.columns else None,
        labels={"Expression": "Expression"},
        box=True,
        points="all",
        title="Violin Plot",
    )
    return violin_figure
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper to scan data directory for allowed files
def scan_files(dir_path: Path) -> list[str]:
    """Return a sorted list of relative file paths under dir_path with allowed extensions."""
    out = []
    for root, _, files in os.walk(dir_path):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in settings.RDS_ALLOWED_EXT:
                rel = p.resolve().relative_to(dir_path)
                out.append(str(rel).replace(os.sep, "/"))
    out.sort()
    return out
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper to parse uploaded config/filter files
def parse_upload(contents: str, filename: str):
    """
    contents is like: 'data:application/json;base64,AAAA...'
    returns python object (dict/list/...) you can store in dcc.Store
    """
    _, b64data = contents.split(",", 1)
    raw = base64.b64decode(b64data)

    # JSON is nice for simple key-value configs, and it's also widely used and supported.
    if filename.lower().endswith(".json"):
        return json.loads(raw.decode("utf-8"))

    # YAML is nice because it can represent complex data structures, and it's also human-readable.
    if filename.lower().endswith((".yaml", ".yml")):
        return yaml.safe_load(raw.decode("utf-8"))

    # If not YAML or JSON, allow plain text filters for the 'Genes' slot
    if filename.lower().endswith(".txt"):
        return {"Genes": raw.decode("utf-8")}

#    raise ValueError(f"Unsupported file type: {filename}")
    raise ValueError(f"Config: {yaml.safe_load(raw.decode('utf-8'))}")
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Ensure that selected cells are in the current data, and that the resulting matrix isn't too large to handle
def validate_selected_cells(selected_cells: list[str], all_cells: list[str], max_cells: int = settings.max_cells) -> tuple[list[str], dbc.Alert | None]:
    # Check if all selected cells are in the current data
    if not all(cell in all_cells for cell in selected_cells):
        raise ValueError("Some selected barcodes are not in the current data!")

    # Check if the number of selected cells is within the limit
    alert = None
    if len(selected_cells) > max_cells:
        selected_cells = selected_cells[:max_cells]  # Trim the list to the max allowed
        alert = dbc.Alert(f"Warning: Too many barcodes selected. Downsampling to maximum {max_cells} barcodes.", color="danger", dismissable=True)

    return list(selected_cells), alert
# -------------------------------------------------------------------
