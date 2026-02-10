import os
import secrets

# CLI Defaults
DEFAULT_IP = os.getenv("DATASCOPE_IP", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("DATASCOPE_PORT", 8050))
DEFAULT_DEBUG = os.getenv("DATASCOPE_DEBUG", "True") == "True"
DEFAULT_RDS_PATH = os.getcwd()  # Default RDS file path is current working directory

# Other Settings
RDS_ALLOWED_EXT = {".rds", ".rda", ".rdata"}  # Allowed file extensions
CACHE_DEFAULT_TIMEOUT = 12 * 60 * 60  # Cache timeout in seconds

max_features = 60  # Maximum number of features to plot at once

# Set the environment variables for default settings - cli may change these
os.environ["DATASCOPE_IP"] = DEFAULT_IP
os.environ["DATASCOPE_PORT"] = str(DEFAULT_PORT)
os.environ["DATASCOPE_DEBUG"] = str(DEFAULT_DEBUG)
os.environ["DATASCOPE_RDS_PATH"] = DEFAULT_RDS_PATH
os.environ["DATASCOPE_TOKEN"] = os.environ.get("DATASCOPE_TOKEN", secrets.token_hex(32))  # 64-character hex string (256 bits)
