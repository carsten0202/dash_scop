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

max_features = 60  # Maximum number of features to plot at once (in violin plots, etc.)
max_ticks_x = 100  # Maximum number of ticks to show on x-axis (e.g. for heatmap plots with many categories)
max_ticks_y = 50  # Maximum number of ticks to show on y-axis (e.g. for heatmap plots with many genes)
max_cells = 2000  # Maximum number of cells to allow for plotting (performance issues and werkzeug timeouts)
max_heatmap_cells = 1000  # Maximum number of cells to display in a heatmap
max_heatmap_genes = 500  # Maximum number of genes to display in a heatmap
heatmap_sampling_seed = 42  # Fixed seed for deterministic heatmap downsampling
