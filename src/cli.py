import os
from pathlib import Path

import click

from app import load_config, main
from settings import DEFAULT_DEBUG, DEFAULT_IP, DEFAULT_PORT, DEFAULT_RDS_PATH

# TODO: Make decision on using os.environ vs parsing the click context default_map for config values.
#   Currently using both, which is redundant and could lead to confusion. The main reason for using os.environ is that
#   it allows the config values to be easily accessed from anywhere in the codebase without needing to pass around the
#   click context. However, it does add some complexity in terms of ensuring that the environment variables are set
#   correctly and are kept in sync with the click context. One option would be to standardize on using the click
#   context for all config values and then only set the environment variables at the point of launching the app, but
#   this would require refactoring some of the code that currently relies on os.environ. Another option would be to
#   continue using both but add some helper functions to abstract away the differences and ensure that they are kept in
#   sync. Overall, I think it would be cleaner to standardize on one approach, but it may require some refactoring to
#   achieve that.
#   PS: From 'Currently...' is AI comment, but may have some truth to it, so kept it around.
#   PPS: Code will currently fail if ctx.default_map is None, which it will be if no config file is provided.

@click.command()
@click.option("--config", type=click.Path(), default=".yaml", callback=load_config, expose_value=False, is_eager=True, help="Path to a JSON or YAML config file.")
@click.option("--debug/--no-debug", is_flag=True, default=DEFAULT_DEBUG, help="Enable Dash debug mode.")
@click.option("--ip", default=DEFAULT_IP, help="IP address to run the Dash app on.")
@click.option("--port", type=int, default=DEFAULT_PORT, help="Port number for the Dash app.")
@click.option("-r", "--rds-path", type=str, default=DEFAULT_RDS_PATH, help="Path to RDS datafile containing one Seurat object.")
@click.pass_context
def cli(ctx, debug, ip, port, rds_path):
    """Launch the Dash app with configurable IP, port, and debug mode."""

    # Set env vars from config file, then update with CLI args (CLI > config > defaults)
    os.environ.update({k:str(v) for k,v in ctx.default_map.items() if ctx.default_map}) # v must be strings to be set as env vars
    os.environ["DATASCOPE_IP"] = ip
    os.environ["DATASCOPE_PORT"] = str(port)
    os.environ["DATASCOPE_DEBUG"] = str(debug)
    os.environ["DATASCOPE_RDS_PATH"] = str(Path(rds_path).resolve())

    main()

if __name__ == "__main__":
    cli()
