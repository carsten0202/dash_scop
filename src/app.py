import os

from dash import Dash

from callbacks import register_callbacks
from data_loader import load_seurat_rds
from layout import layout

# Initialize Dash app
app = Dash(__name__)
app.layout = layout

# Register callbacks
register_callbacks(app)

def main():
    ip = os.getenv("DASH_IP", "127.0.0.1")
    port = int(os.getenv("DASH_PORT", 8050))
    debug = os.getenv("DASH_DEBUG", "True") == "True"

    app.run_server(host=ip, port=port, debug=debug)


if __name__ == "__main__":
    main()
