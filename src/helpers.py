import base64
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import rpy2.robjects as ro
import yaml
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import localconverter
from scipy.stats import zscore

import settings


# -------------------------------------------------------------------
# Helper to fetch expression subset for given genes and cells
def fetch_expression_subset(
    seurat_handle: str,
    genes: list[str] | None = None,
    cells: list[str] | None = None,
) -> pd.DataFrame:
    with localconverter(ro.default_converter + pandas2ri.converter):
        r_genes = ro.StrVector(genes) if genes else ro.NULL
        r_cells = ro.StrVector(cells) if cells else ro.NULL
        mat = ro.r["get_expression_subset_matrix"](seurat_handle, r_genes, r_cells) # type: ignore

    if not isinstance(mat, pd.DataFrame):
        mat = pd.DataFrame(mat)

    return mat
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
def generate_boxplot(boxplot_df, selected_barcodes, shape_column, gene, barcodes_color):
    """Generate a boxplot figure."""
    if shape_column and shape_column in boxplot_df.columns:  # If shape column is specified and exists
        fig = px.box(
            boxplot_df.loc[selected_barcodes, [shape_column, gene]],
            x=shape_column,
            y=gene,
            color=barcodes_color[selected_barcodes] if barcodes_color is not None else None,
            labels={shape_column: shape_column, gene: "Expression"},
            title=f"Boxplot for {gene}",
        )
    else:
        fig = px.box(  # If no shape column, plot all in one box
            boxplot_df.loc[selected_barcodes, gene],
            y=gene,
            labels={gene: "Expression"},
            color=barcodes_color[selected_barcodes] if barcodes_color is not None else None,
            title=f"Boxplot for {gene}",
        )
    return fig
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Helper to generate a heatmap figure
def generate_heatmap(matrix_df, selected_genes, selected_barcodes):
    heatmap_df = matrix_df.apply(
        lambda row: pd.Series(
            np.asarray(zscore(row, nan_policy="omit")),
            index=row.index,
            dtype=float,
        ),
        axis=1,
        result_type="broadcast",
    )
    heatmap_figure = px.imshow(
        heatmap_df,
        color_continuous_scale="Viridis",
        title="Gene Expression Heatmap",
        x=heatmap_df.columns,  # columns
        y=selected_genes,  # rows
        aspect="auto",
        # aspect="equal",
        labels=dict(x="Cells", y="Genes", color="Expr"),  # axis titles & color-bar
    )

    # Don't show labels if there's too many
    if len(selected_genes) > settings.max_features:
        heatmap_figure.update_yaxes(showticklabels=False)
    if len(selected_barcodes) > 2 * settings.max_features:
        heatmap_figure.update_xaxes(showticklabels=False)

    return heatmap_figure
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
