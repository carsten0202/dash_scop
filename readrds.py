
import rpy2.robjects as ro
from rpy2.robjects import r
#import pandas as pd

# Load the RDS file
try:
	rds_file = "testdata/20220818_brain_10x-test_rna-seurat.rds"
	r_object = ro.r['readRDS'](rds_file)
except:
	print("Unable to read RDS file")

import pandas as pd
df = pd.read_csv("testdata/20220818_brain_10x-test_rna-seurat.csv")

# If the R object is a data frame, you can convert it to a pandas DataFrame
#if isinstance(r_object, ro.vectors.DataFrame):
#    df = pd.DataFrame({col: list(r_object[col]) for col in r_object.names})
