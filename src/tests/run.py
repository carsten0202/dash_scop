import socket
import subprocess


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
    # Find a free port
    port = find_free_port(start=25000, end=26000)

    # Set any other parameters you need
    ip = "0.0.0.0"
    rds_file = "/app/data/data.rds"  # adjust if necessary
    cli_script = "/app/cli.py"
    python_exec = "/app//.venv/bin/python3"
    container = "dash_scop_latest.sif"

    # Build the singularity exec command
    cmd = [
        "singularity",
        "exec",
        "--cleanenv",
        container,
        python_exec,
        cli_script,
        "--ip",
        ip,
        "--port",
        str(port),
        "--rds",
        rds_file,
    ]

    # Print info form debugging
    print(f"Launching app on port {port}...")
    print("Running command:", " ".join(cmd))

    # Launch
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
