
import scanpy as sc

# Load the converted h5ad file
adata = sc.read_h5ad("testdata/seurat_data.h5ad")

print(adata)
print(adata.obsm)
print(adata.obsm['X_umap'])
