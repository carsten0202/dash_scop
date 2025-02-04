
import pandas as pd
from rpy2.robjects import r
from rpy2.robjects import pandas2ri

rds_file = "testdata/20220818_brain_10x-test_rna-seurat.rds"

# Load the RDS file
try:
	r_obj = r['readRDS'](rds_file)
	r_dgC = r['LayerData'](r_obj, assay = "SCT", layer = "counts")
except Exception as e:
	print(e)
	print("Unable to read RDS file")

r_df  = r['as.data.frame'](r_dgC)
pandas2ri.activate()
df = pandas2ri.rpy2py(r_df)

#import rpy2.robjects as ro
#with (ro.default_converter + pandas2ri.converter).context():
#  df = ro.conversion.get_conversion().rpy2py(r_df)

print(df.transpose())

