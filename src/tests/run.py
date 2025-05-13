import argparse
import os
import socket
import subprocess
import sys


def find_free_port(start=8000, end=9000):
    """Find a free port in the given range."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start}-{end}")


def main():
    parser = argparse.ArgumentParser(description="Launch Singularity container with auto-selected port and data file.")
    parser.add_argument("--data", default="/app/data/data.rds", help="Path to the .rds data file")
    parser.add_argument("--container", default="dash_scop_latest.sif", help="Singularity container file")
    parser.add_argument("--port-start", type=int, default=8000, help="Port search start")
    parser.add_argument("--port-end", type=int, default=9000, help="Port search end")

    args = parser.parse_args()

    # Resolve and validate data path
    host_data_path = os.path.abspath(args.data)
    if not os.path.isfile(host_data_path):
        print(f"ERROR: Data file not found: {host_data_path}")
        sys.exit(1)

    # Find a free port
    port = find_free_port(start=25000, end=26000)

    # Set any other parameters you need
    ip = "0.0.0.0"
    cli_script = "/app/cli.py"
    python_exec = "/app/.venv/bin/python3"
    container_data_path = "/data/data.rds"

    # Build the singularity exec command
    cmd = [
        "singularity",
        "exec",
        "--bind",
        f"{host_data_path}:{container_data_path}",  # bind host data into container
        args.container,
        python_exec,
        cli_script,
        "--cleanenv",
        "--ip",
        ip,
        "--port",
        str(port),
        "--rds",
        container_data_path,
    ]

    # Run
    print(f"Launching on port {port} using data file: {host_data_path}")
    # Print info for debugging
    print("Running command:", " ".join(cmd))

    # Launch
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
