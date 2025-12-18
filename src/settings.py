import os
from pathlib import Path

# CLI Defaults
DEFAULT_IP = os.getenv("DASH_IP", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("DASH_PORT", 8050))
DEFAULT_DEBUG = os.getenv("DASH_DEBUG", "True") == "True"
DEFAULT_RDS_PATH = os.getcwd()  # Default RDS file path is current working directory

# Other Settings
RDS_ALLOWED_EXT = {".rds", ".rda", ".rdata"}  # Allowed file extensions
CACHE_DEFAULT_TIMEOUT = 12 * 60 * 60  # Cache timeout in seconds

max_features = 60  # Maximum number of features to plot at once
