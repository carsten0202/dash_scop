import os
import secrets

# CLI Defaults
DEFAULT_IP = os.getenv("DATASCOPE_IP", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("DATASCOPE_PORT", 8050))
DEFAULT_DEBUG = os.getenv("DATASCOPE_DEBUG", "True") == "True"
DEFAULT_RDS_PATH = os.getenv("DATASCOPE_RDS_PATH", os.getcwd())  # Default RDS file path is current working directory

# Set a default token if not provided via environment variable (not recommended for production)
DATASCOPE_TOKEN = os.environ.get("DATASCOPE_TOKEN", secrets.token_hex(32))  # 64-character hex string (256 bits)

# Other Settings
RDS_ALLOWED_EXT = {".rds", ".rda", ".rdata"}  # Allowed file extensions
CACHE_DEFAULT_TIMEOUT = 12 * 60 * 60  # Cache timeout in seconds

max_features = 60  # Maximum number of features to plot at once

