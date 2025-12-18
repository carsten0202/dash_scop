import json
import os
import secrets

import click
import yaml

from settings import DEFAULT_DEBUG, DEFAULT_IP, DEFAULT_PORT, DEFAULT_RDS_PATH


@click.command()
@click.option("--config", type=click.Path(exists=True), help="Path to a JSON or YAML config file.")
@click.option("--debug", is_flag=True, default=DEFAULT_DEBUG, help="Enable Dash debug mode.")
@click.option("--ip", help="IP address to run the Dash app on.")
@click.option("--port", type=int, help="Port number for the Dash app.")
@click.option("-r", "--rds", type=str, help="Path to RDS datafile containing one Seurat object.")
def run(config, debug, ip, port, rds):
    """Launch the Dash app with configurable IP, port, and debug mode."""
    config_data = load_config(config) if config else {}

    ip = ip or config_data.get("ip", DEFAULT_IP)
    port = port or config_data.get("port", DEFAULT_PORT)
    debug = debug if debug is not None else config_data.get("debug", DEFAULT_DEBUG)
    rds = rds or config_data.get("rds", DEFAULT_RDS_PATH)

    os.environ["DASH_IP"] = ip
    os.environ["DASH_PORT"] = str(port)
    os.environ["DASH_DEBUG"] = str(debug)
    os.environ["DASH_RDS_PATH"] = rds

    from app import main  # Import after setting env variables

    main(config_data)


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
    os.environ["DASH_TOKEN"] = os.environ.get("DASH_TOKEN", secrets.token_hex(32))  # 64-character hex string (256 bits)
    run()
