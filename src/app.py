import os
import secrets

from dash import Dash
from werkzeug.wrappers import Request, Response

from callbacks import register_callbacks
from layout import get_layout

# Initialize Dash app
app = Dash(__name__)

# Register callbacks
register_callbacks(app)


# Custom middleware that checks token in URL
class TokenAuthMiddleware:
    def __init__(self, app, token):
        self.app = app
        self.token = token

    def __call__(self, environ, start_response):
        request = Request(environ)
        if request.args.get("token") != self.token:  # Respond with 403 Forbidden
            res = Response("403 Forbidden: Invalid or missing token", status=403)
            return res(environ, start_response)
        return self.app(environ, start_response)


def main(config_data):
    ip = os.getenv("DASH_IP", "127.0.0.1")
    port = str(os.getenv("DASH_PORT", "8050"))
    debug = os.getenv("DASH_DEBUG", "True") == "True"
    token = os.environ.get("DASH_TOKEN", "SECRET_TOKEN")  # 64-character hex string (256 bits)

    import traceback

    traceback.print_stack()

    print(f"Dash app available at http://{ip}:{port}/?token={token}")

    app.server.wsgi_app = TokenAuthMiddleware(app.server.wsgi_app, token)  # Wrap with middleware
    app.layout = get_layout(config_data)
    # app.run(host=ip, port=port, debug=debug)


# if __name__ == "__main__":
#    main({})
