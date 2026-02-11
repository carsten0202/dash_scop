import json
import os
from pathlib import Path

import click
import yaml

from settings import DEFAULT_DEBUG, DEFAULT_IP, DEFAULT_PORT, DEFAULT_RDS_PATH


def load_config(ctx, param, config):
    """Load configuration from a YAML or JSON file."""
    print(f"Parsing config data: {config}; {type(config)}")
    if config:
        with open(config, "r") as f:
            if config.endswith(".json"):
                ctx.default_map = json.load(f)
            elif config.endswith(".yaml") or config.endswith(".yml"):
                ctx.default_map = yaml.safe_load(f)
            else:
                raise ValueError("Unsupported config file format. Use JSON or YAML.")
        print(f"Parsing config data: {ctx.default_map}")
    return config


@click.command()
@click.option("--config", type=click.Path(exists=True), default=".yaml", callback=load_config, expose_value=False, is_eager=True, help="Path to a JSON or YAML config file.")
@click.option("--debug/--no-debug", is_flag=True, default=DEFAULT_DEBUG, help="Enable Dash debug mode.")
@click.option("--ip", help="IP address to run the Dash app on.")
@click.option("--port", type=int, help="Port number for the Dash app.")
@click.option("-r", "--rds", type=str, default=DEFAULT_RDS_PATH, help="Path to RDS datafile containing one Seurat object.")
@click.pass_context
def cli(ctx, debug, ip, port, rds):
    """Launch the Dash app with configurable IP, port, and debug mode."""
#    config_data = load_config(config) if config else {}
    config_data = {}

#    ip = ip or config_data.get("ip", DEFAULT_IP)
#    port = port or config_data.get("port", DEFAULT_PORT)
#    debug = debug if debug is not None else config_data.get("debug", DEFAULT_DEBUG)
#    rds = rds or config_data.get("rds", DEFAULT_RDS_PATH)
    print(f"CLI args: ip={ip}, port={port}, debug={debug}, rds={rds}")

    os.environ["DATASCOPE_IP"] = ip
    os.environ["DATASCOPE_PORT"] = str(port)
    os.environ["DATASCOPE_DEBUG"] = str(debug)
    os.environ["DATASCOPE_RDS_PATH"] = str(Path(rds).resolve())

#    from app import main  # Import after setting env variables
    import app

    app.main(config_data)

if __name__ == "__main__":
    cli()