import json
import os

import click
import yaml

DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = 8050
DEFAULT_DEBUG = True


@click.command()
@click.option("--config", type=click.Path(exists=True), help="Path to a JSON or YAML config file.")
@click.option("--ip", default=DEFAULT_IP, help="IP address to run the Dash app on.")
@click.option("--port", default=DEFAULT_PORT, type=int, help="Port number for the Dash app.")
@click.option("--debug", is_flag=True, default=DEFAULT_DEBUG, help="Enable Dash debug mode.")
def run(config, ip, port, debug):
    """Launch the Dash app with configurable IP, port, and debug mode."""

    config_data = load_config(config) if config else {}

    ip = ip or config_data.get("ip", DEFAULT_IP)
    port = port or config_data.get("port", DEFAULT_PORT)
    debug = debug if debug is not None else config_data.get("debug", DEFAULT_DEBUG)

    os.environ["DASH_IP"] = ip
    os.environ["DASH_PORT"] = str(port)
    os.environ["DASH_DEBUG"] = str(debug)

    from app import main  # Import after setting env variables

    main()


def load_config(config_file):
    """Load configuration from a YAML or JSON file."""
    if not config_file:
        return {}

    if config_file.endswith(".json"):
        with open(config_file, "r") as f:
            return json.load(f)
    elif config_file.endswith(".yaml") or config_file.endswith(".yml"):
        with open(config_file, "r") as f:
            return yaml.safe_load(f)
    else:
        raise ValueError("Unsupported config file format. Use JSON or YAML.")


if __name__ == "__main__":
    run()
