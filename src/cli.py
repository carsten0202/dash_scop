import os
from pathlib import Path

import click

from app import load_config, main
from settings import DEFAULT_DEBUG, DEFAULT_IP, DEFAULT_PORT, DEFAULT_RDS_PATH


@click.command()
@click.option("--config", type=click.Path(exists=True), default=".yml", callback=load_config, expose_value=False, is_eager=True, help="Path to a JSON or YAML config file.")
@click.option("--debug/--no-debug", is_flag=True, default=DEFAULT_DEBUG, help="Enable Dash debug mode.")
@click.option("--ip", default=DEFAULT_IP, help="IP address to run the Dash app on.")
@click.option("--port", type=int, default=DEFAULT_PORT, help="Port number for the Dash app.")
@click.option("-r", "--rds-path", type=str, default=DEFAULT_RDS_PATH, help="Path to RDS datafile containing one Seurat object.")
@click.pass_context
def cli(ctx, debug, ip, port, rds_path):
    """Launch the Dash app with configurable IP, port, and debug mode."""

    # Set env vars from config file, then update with CLI args (CLI > config > defaults)
    os.environ.update({k:str(v) for k,v in ctx.default_map.items()}) # v must be strings to be set as env vars
    os.environ["DATASCOPE_IP"] = ip
    os.environ["DATASCOPE_PORT"] = str(port)
    os.environ["DATASCOPE_DEBUG"] = str(debug)
    os.environ["DATASCOPE_RDS_PATH"] = str(Path(rds_path).resolve())

    main()

if __name__ == "__main__":
    cli()
