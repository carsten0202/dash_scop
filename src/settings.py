import os
from pathlib import Path

# CLI Defaults
DEFAULT_IP = os.getenv("DASH_IP", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("DASH_PORT", 8050))
DEFAULT_DEBUG = os.getenv("DASH_DEBUG", "True") == "True"
DEFAULT_RDS_FILE = "testdata/seurat_obj_downsampled.rds"

# Other Settings
BASE_DIR = Path(os.getenv("BASE_DIR", "testdata")).resolve(strict=False)  # Base directory for data files
RDS_ALLOWED_EXT = {".rds", ".rda", ".rdata"}  # Allowed file extensions

max_features = 60  # Maximum number of features to plot at once
combined_barcodes_colname = "Combined"  # Setting for combined feature column name
