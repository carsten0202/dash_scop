# app.py
import os
import time
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html, no_update
from flask import Flask
from rpy2 import robjects

# --- Settings
BASE_DIR = Path("/srv/dash-data/seurat").resolve()  # your server folder
ALLOWED_EXT = {".rds"}  # adjust as needed

server = Flask(__name__)
app = Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP])


def scan_files():
    """Return a sorted list of relative file paths under BASE_DIR with allowed extensions."""
    out = []
    for root, _, files in os.walk(BASE_DIR):
        for f in files:
            p = Path(root) / f
            if p.suffix.lower() in ALLOWED_EXT:
                rel = p.resolve().relative_to(BASE_DIR)
                out.append(str(rel).replace(os.sep, "/"))
    out.sort()
    return out


app.layout = dbc.Container(
    [
        html.H4("Select data file from server"),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Dropdown(
                        id="file-dropdown",
                        options=[],  # filled by callback
                        placeholder=f"Browse {BASE_DIR}…",
                        searchable=True,
                        clearable=False,
                        style={"width": "100%"},
                    ),
                    md=8,
                ),
                dbc.Col(
                    dbc.Button("Rescan", id="rescan", n_clicks=0, color="secondary"),
                    md=2,
                ),
                dbc.Col(
                    dbc.Checklist(
                        options=[{"label": "Show subfolders", "value": "sub"}],
                        value=["sub"],
                        id="show-subfolders",
                        switch=True,
                    ),
                    md=2,
                ),
            ],
            className="gy-2",
        ),
        html.Div(id="selected-info", className="mt-3"),
        dcc.Store(id="file-list"),
        dcc.Interval(id="init", interval=50, n_intervals=0, max_intervals=1),  # populate once on load
    ],
    fluid=True,
)


@app.callback(
    Output("file-list", "data"),
    Input("rescan", "n_clicks"),
    Input("init", "n_intervals"),
    prevent_initial_call=True,
)
def refresh_file_list(_clicks, _init):
    files = scan_files()
    # include simple metadata (mtime, size) if you like
    enriched = []
    for rel in files:
        p = (BASE_DIR / rel).resolve()
        st = p.stat()
        enriched.append(
            {
                "rel": rel,
                "size": st.st_size,
                "mtime": int(st.st_mtime),
            }
        )
    return enriched


@app.callback(
    Output("file-dropdown", "options"),
    Input("file-list", "data"),
    Input("show-subfolders", "value"),
)
def populate_dropdown(file_list, show_flags):
    if not file_list:
        return []
    show_sub = "sub" in (show_flags or [])
    opts = []
    for item in file_list:
        rel = item["rel"]
        label = rel if show_sub else Path(rel).name
        opts.append({"label": label, "value": rel})
    return opts


def safe_abs_path(rel_path: str) -> Path:
    """Resolve a user-chosen relative path into an absolute path under BASE_DIR safely."""
    abs_p = (BASE_DIR / rel_path).resolve()
    if not str(abs_p).startswith(str(BASE_DIR)):  # prevent path traversal
        raise ValueError("Invalid path selection")
    return abs_p


# ---- Hook up loading the Seurat object (example)

readRDS = robjects.r["readRDS"]

# (Optional) tiny cache so repeated selections are fast
_LOADED = {}  # key: (abs_path, mtime) -> R object


def load_seurat(abs_path: Path):
    st = abs_path.stat()
    key = (str(abs_path), int(st.st_mtime))
    if key not in _LOADED:
        _LOADED.clear()  # keep it tiny; or use functools.lru_cache
        _LOADED[key] = readRDS(str(abs_path))
    return _LOADED[key]


@app.callback(
    Output("selected-info", "children"),
    Input("file-dropdown", "value"),
    State("file-list", "data"),
    prevent_initial_call=True,
)
def handle_selection(rel_value, file_list):
    if not rel_value:
        return no_update
    abs_p = safe_abs_path(rel_value)
    try:
        obj = load_seurat(abs_p)  # <-- you now have the Seurat object via rpy2
        # You probably won't want to send the object to the browser; just confirm and kick off downstream steps.
        st = abs_p.stat()
        return dbc.Alert(
            [
                html.Strong("Loaded: "),
                html.Code(str(abs_p)),
                html.Br(),
                f"Size: {st.st_size / 1_048_576:.2f} MB · Modified: {time.ctime(st.st_mtime)}",
            ],
            color="success",
            dismissable=True,
        )
    except Exception as e:
        return dbc.Alert(f"Failed to load: {e}", color="danger", dismissable=True)


if __name__ == "__main__":
    app.run(debug=True)
