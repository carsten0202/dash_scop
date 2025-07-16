import os

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


# Define your secret token
# SECRET_TOKEN = os.environ.get("DASH_TOKEN", "abc123secretHEX")


def main(config_data):
    ip = os.getenv("DASH_IP", "127.0.0.1")
    port = str(os.getenv("DASH_PORT", 8050))
    debug = os.getenv("DASH_DEBUG", "True") == "True"

    app.layout = get_layout(config_data)
    app.server.wsgi_app = TokenAuthMiddleware(app.server.wsgi_app, "SECRET_TOKEN")  # Wrap with middleware
    app.run(host=ip, port=port, debug=debug)

    # Wait a moment for server to start
    # time.sleep(1)
    print(f"📊 Dash app available at http://{ip}:{port}/?token={debug}")


if __name__ == "__main__":
    main({})
