#!/opt/software/python/3.12.8/bin/python

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
    parser = argparse.ArgumentParser(description="Launch DataSCOPE container with auto-selected port and data file.")
    parser.add_argument("--data", default=os.getcwd(), help="Path to directory with .rds data files")
    parser.add_argument(
        "--container",
        default=os.getenv("DSCOPE_CONTAINER_PATH", "datascope_latest.sif"),
        help="Apptainer/Singularity container file",
    )
    parser.add_argument("--port-start", type=int, default=8800, help="Port search start")
    parser.add_argument("--port-end", type=int, default=9000, help="Port search end")

    args = parser.parse_args()

    # Resolve and validate data path
    host_data_path = os.path.abspath(args.data)
    if not os.path.isdir(host_data_path):
        print(f"ERROR: Data directory not found (or it isn't a directory): {host_data_path}")
        sys.exit(1)

    # Find a free port and record hostname
    port = find_free_port(start=args.port_start, end=args.port_end)
    hostname = socket.gethostname()

    # Set any other parameters you need
    ip = socket.gethostbyname(hostname)
    cli_script = "/app/cli.py"
    python_exec = "/app/.venv/bin/python3"
    container_data_path = "/app/data"

    # Build the apptainer exec command
    cmd = [
        "apptainer",
        "exec",
        "--cleanenv",
        "--bind",
        f"{host_data_path}:{container_data_path}",  # bind host data into container
        args.container,
        python_exec,
        cli_script,
        "--ip",
        ip,
        "--port",
        str(port),
        "--rds",
        container_data_path,
        "--no-debug",
    ]

    # Run
    print(f"Launching on port {port} using data path: {host_data_path}")
    # Print info for debugging
    print("Running command:", " ".join(cmd))

    # Launch
    subprocess.run(cmd)


if __name__ == "__main__":

    hostname = socket.gethostname()
    IPAddr = socket.gethostbyname(hostname)

    print("Your Computer Name is:", hostname)
    print("Your Computer IP Address is:", IPAddr)

    main()
