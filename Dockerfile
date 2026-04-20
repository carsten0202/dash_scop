# syntax=docker/dockerfile:1

# 1) Start from official Python slim image
FROM python:3.12-slim-bookworm

# 2) Install tools needed for GPG + HTTPS + repos
RUN apt-get update && apt-get install -y --no-install-recommends \
    dirmngr \
    gnupg \
    ca-certificates \
    software-properties-common \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 3) Import the current CRAN Debian key and add the bookworm-cran40 repo
#    Key fingerprint: 95C0 FA F3 8D B3 CC AD 0C 08 0A 7B DC 78 B2 DD EA BC 47 B7
RUN set -eux; \
    gpg --batch --keyserver hkp://keyserver.ubuntu.com:80 \
    --recv-key '95C0FAF38DB3CCAD0C080A7BDC78B2DDEABC47B7'; \
    gpg --armor --export '95C0FAF38DB3CCAD0C080A7BDC78B2DDEABC47B7' \
    > /etc/apt/trusted.gpg.d/cran_debian_key.asc; \
    echo 'deb http://cloud.r-project.org/bin/linux/debian bookworm-cran40/' \
    > /etc/apt/sources.list.d/cran.list

# 4) Install R (latest from CRAN backport for Debian bookworm)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    cmake \
    pkg-config \
    r-base \
    r-base-dev \
    libuv1-dev \
    libcurl4-openssl-dev \
    libxml2-dev \
    libssl-dev \
    libgit2-dev \
    libcairo2-dev \
    libhdf5-dev \
    libudunits2-dev \
    libfftw3-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libfontconfig1-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libfreetype6-dev \
    libpng-dev \
    libtiff5-dev \
    libjpeg-dev \
    libbz2-dev \
    liblzma-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Ensure R can install and find packages in the site library
RUN mkdir -p /usr/local/lib/R/site-library && chmod -R 777 /usr/local/lib/R/site-library
ENV R_LIBS_SITE=/usr/local/lib/R/site-library
ENV R_LIBS_USER=/blah

# 5) Install BiocManager
RUN R --quiet -e 'options(repos = c(CRAN = "https://cloud.r-project.org")); if (!requireNamespace("BiocManager", quietly = TRUE)) install.packages("BiocManager")'

# 6) Install Bioconductor packages used by the app
RUN R --quiet -e 'options(repos = c(CRAN = "https://cloud.r-project.org")); BiocManager::install(c("multtest", "AnnotationDbi", "org.Hs.eg.db", "org.Mm.eg.db", "org.Rn.eg.db", "SingleCellExperiment"), ask = FALSE, update = FALSE)'

# 7) Install Seurat runtime dependencies only
RUN R --quiet -e 'options(repos = c(CRAN = "https://cloud.r-project.org", "https://satijalab.r-universe.dev", "https://bnprks.r-universe.dev")); install.packages("Seurat", dependencies = c("Depends", "Imports", "LinkingTo"))'

# 8) Verify required R packages explicitly
RUN R --quiet -e 'stopifnot(requireNamespace("SingleCellExperiment", quietly = TRUE)); stopifnot(requireNamespace("AnnotationDbi", quietly = TRUE))'
RUN R --quiet -e 'stopifnot(requireNamespace("Seurat", quietly = TRUE)); packageVersion("Seurat"); print("Seurat installed successfully")'

# Create a non-privileged user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser


# Switch to the non-privileged user and set up Workdir
USER appuser
WORKDIR /app
COPY requirements.txt .


# Install Python dependencies (including rpy2) into venv
RUN python3 -m venv .venv && \
    .venv/bin/python3 -m pip install --upgrade pip && \
    .venv/bin/python3 -m pip install -r requirements.txt && \
    .venv/bin/python3 -c "import rpy2.robjects as ro; from rpy2.robjects.packages import importr; seurat = importr('Seurat'); print('rpy2 Seurat import successful')"

COPY src .

# Expose and run
EXPOSE 8050
CMD ["/app/.venv/bin/python3", "/app/cli.py", "--ip", "0.0.0.0", "--port", "8050"]
