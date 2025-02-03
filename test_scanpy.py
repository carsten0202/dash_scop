
import scanpy as sc

# Load the converted h5ad file
adata = sc.read_h5ad("testdata/seurat_data.h5ad")

print(adata)
print(adata.obsm)
print(adata.obsm['X_umap'])

# Now you can use Plotly and Dash for visualization
import plotly.express as px
# fig = px.scatter(x=adata.obsm['X_pca'][:, 0], y=adata.obsm['X_pca'][:, 1], color=adata.obs['cell_type'])
# fig.show()
