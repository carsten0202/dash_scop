# DataSCOPe

DataSCOPe is a Dash-based web app for visualizing and quality-checking single-cell omics data stored as Seurat objects in R `.rds` files.

It is designed for interactive exploration of cell metadata, gene expression, and embeddings without requiring users to write plotting code for common QC and inspection tasks.

## Quick Start

1. Install Python dependencies.
2. Make sure R and the required R packages are available.
3. Start the app and point it at a folder containing Seurat files.
4. Open the printed URL in your browser.
5. Load a dataset, apply filters, and generate plots.

Example:

```bash
pip install -e .
dash-app --rds-path /path/to/seurat/files
```

If token protection is enabled, open the full URL printed in the terminal, including `?token=...`.

## Features

- Browse and load Seurat datasets from a configured directory
- Explore cell-level metadata through interactive barcode filters
- Select genes by ID or mapped gene symbol when available
- Generate `UMAP`, `violin`, `boxplot`, and `heatmap` views
- Save active filters to YAML and upload them again later
- Export generated plots as SVG files

## Requirements

You need both Python and R available on the machine running the app.

### Python

- Python 3.12 or newer is recommended
- `pip` for installing dependencies

### R

- A working R installation
- The `Seurat` and `stats` packages installed in R

Optional R packages can improve gene symbol mapping for Ensembl IDs:

- `AnnotationDbi`
- `org.Hs.eg.db`
- `org.Mm.eg.db`
- `org.Rn.eg.db`

## Installation

Install the app in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Alternative install from `requirements.txt`:

```bash
pip install -r requirements.txt
```

Note: `rpy2` depends on a working R installation and may fail to install if R is missing or not visible in your environment.

## Running The App

The packaged CLI entrypoint is:

```bash
dash-app --rds-path /path/to/seurat/files
```

Useful options:

```bash
dash-app --rds-path /path/to/seurat/files --ip 127.0.0.1 --port 8050 --debug
```

Available CLI options:

- `--config`: load settings from a YAML or JSON config file
- `--debug/--no-debug`: enable or disable Dash debug mode
- `--ip`: IP address to bind to
- `--port`: port to bind to
- `--rds-path`: directory containing Seurat files

## Configuration

Configuration can come from CLI flags, environment variables, or a config file.

### Environment Variables

- `DATASCOPE_IP`: host IP for the Dash server
- `DATASCOPE_PORT`: port for the Dash server
- `DATASCOPE_DEBUG`: `True` or `False`
- `DATASCOPE_RDS_PATH`: directory scanned for `.rds`, `.rda`, and `.rdata` files
- `DATASCOPE_TOKEN`: optional access token added as a query parameter

Example:

```bash
export DATASCOPE_RDS_PATH=/data/seurat
export DATASCOPE_PORT=8052
export DATASCOPE_TOKEN=my-token
dash-app
```

### Config File

You can pass a YAML or JSON config file:

```bash
dash-app --config path/to/config.yaml
```

Example YAML:

```yaml
ip: 127.0.0.1
port: 8052
debug: true
rds_path: /data/seurat
```

CLI arguments override config file values.

## Input Data Expectations

DataSCOPe is built for Seurat objects saved in R data files.

Expected characteristics:

- Input files are typically `.rds`
- The app reads a Seurat object from disk through `rpy2`
- Cell metadata is used to build barcode filters
- UMAP embeddings are used for the scatter plot view
- Expression data is read from the selected assay and layer

Current loader defaults expect:

- assay: `SCT`
- layer: `data`

If your object uses different assay or layer names, the current app may need code changes before it can load the dataset correctly.

## Using The App

Typical workflow:

1. Start the app.
2. Open the URL printed in the terminal.
3. Select a dataset from the `Data source` dropdown.
4. Open `Barcode Filter Panel` to filter cells using metadata columns.
5. Open `Gene Filter Panel` to choose genes for expression-based plots.
6. Choose a plot type.
7. Export the current plot as SVG if needed.
8. Save your filters to YAML for reuse later.

### Plot Types

- `UMAP Scatterplot`: inspect embeddings, colored or shaped by metadata
- `Violin Plot`: compare expression distributions across groups
- `Boxplot`: inspect expression spread for selected genes
- `Heatmap`: review expression patterns across genes and filtered cells

### Filter Files

Saved filter files can include:

- selected dataset path
- selected genes
- selected gene IDs
- active metadata filters
- color and shape settings

This makes it easier to return to a previous view or share a plotting setup with a colleague.

## Access Control

If `DATASCOPE_TOKEN` is set, the app requires the token in the URL query string.

Example:

```text
http://127.0.0.1:8050/?token=my-token
```

If no token is set, the app still runs, but the server logs a warning. This token mechanism is lightweight request gating, not a full authentication system.

## Performance Notes

Large single-cell datasets can be expensive to plot interactively. The app includes a few built-in limits to keep plotting manageable.

Current settings include caps such as:

- maximum number of features shown at once
- maximum number of cells allowed for plotting
- lower limits for heatmap cells and genes

If a plot request is too large, the app may reject it and ask you to narrow the filters or reduce the number of selected genes or cells.

## Troubleshooting

### `ImportError` for Seurat or R packages

Make sure the required R packages are installed in the same R environment seen by `rpy2`.

### App starts but no files appear in the dropdown

Check that:

- `DATASCOPE_RDS_PATH` or `--rds-path` points to the correct directory
- your files use supported extensions
- the app process has permission to read the directory

### Dataset fails to load

Common causes:

- the file does not contain a compatible Seurat object
- the expected assay or layer is missing
- the object does not contain the expected UMAP embedding
- the R environment is missing required dependencies

## Project Layout

For advanced users who want to inspect the code:

- `src/app.py`: app startup and request middleware
- `src/cli.py`: command-line entrypoint
- `src/layout.py`: Dash layout and controls
- `src/callbacks.py`: interactive app behavior
- `src/data_loader.py`: Seurat and `rpy2` data loading
- `src/helpers.py`: plotting and filtering helpers
- `src/settings.py`: runtime defaults and limits

## Development Notes

This repository also includes developer tooling such as `ruff`, `mypy`, and `pytest`, but the primary use case is running the app locally against Seurat datasets.

Full verification may depend on local R, `rpy2`, and Seurat availability.
