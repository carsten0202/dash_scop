import os

import dash_bootstrap_components as dbc
from dash import Dash
from werkzeug.wrappers import Request, Response

from callbacks import register_callbacks
from layout import get_layout

# Initialize Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])


# Custom middleware that checks token in URL
class TokenAuthMiddleware:
    def __init__(self, app, token):
        self.app = app
        self.token = token

    def __call__(self, environ, start_response):
        request = Request(environ)

        # Allow Dash internal and static routes
        if request.path.startswith("/_dash-") or request.path.startswith("/assets/"):
            return self.app(environ, start_response)

        # Allow favicon or other extras if needed
        if request.path in ["/favicon.ico"]:
            return self.app(environ, start_response)

        # Otherwise, check token
        if request.args.get("token") != self.token:  # Respond with 403 Forbidden
            res = Response("403 Forbidden: Invalid or missing token", status=403)
            return res(environ, start_response)

        return self.app(environ, start_response)


def main(config_data):
    ip = os.getenv("DATASCOPE_IP", "127.0.0.1")
    port = str(os.getenv("DATASCOPE_PORT", "8050"))
    debug = os.getenv("DATASCOPE_DEBUG", "True") == "True"
    token = os.environ.get("DATASCOPE_TOKEN", "SECRET_TOKEN")  # 64-character hex string (256 bits)

    print(f"\n[INFO] Dash app available at http://{ip}:{port}/?token={token}")

    app.server.wsgi_app = TokenAuthMiddleware(app.server.wsgi_app, token)  # Wrap with middleware
    app.layout = get_layout(config_data)
    register_callbacks(app) # Register callbacks
    app.run(host=ip, port=port, debug=debug)


if __name__ == "__main__":
    main({})
