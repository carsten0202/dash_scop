import os

from dash import Dash

from callbacks import register_callbacks
from layout import get_layout

# Initialize Dash app
app = Dash(__name__)

# Register callbacks
register_callbacks(app)


def main(config_data):
    ip = os.getenv("DASH_IP", "127.0.0.1")
    port = str(os.getenv("DASH_PORT", 8050))
    debug = os.getenv("DASH_DEBUG", "True") == "True"

    app.layout = get_layout(config_data)
    app.run(host=ip, port=port, debug=debug)


if __name__ == "__main__":
    main({})
