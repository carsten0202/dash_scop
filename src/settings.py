import os
from pathlib import Path

BASE_DIR = Path(os.getenv("BASE_DIR", "testdata")).resolve(strict=False)  # Base directory for data files
RDS_ALLOWED_EXT = {".rds", ".rda", ".rdata", ".csv"}  # Allowed file extensions

max_features = 60  # Maximum number of features to plot at once
