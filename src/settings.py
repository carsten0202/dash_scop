import os
from pathlib import Path

BASE_DIR = Path(os.getenv("BASE_DIR", "testdata")).resolve(strict=False)
ALLOWED_EXT = {".rds", ".rda", ".rdata", ".csv", ".tsv", ".txt"}
