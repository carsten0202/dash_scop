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
    r-base \
    r-base-dev \
    libcurl4-openssl-dev \
    libxml2-dev \
    libssl-dev \
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

# 5) Install Seurat and dependencies
RUN mkdir -p /usr/local/lib/R/site-library && chmod -R 777 /usr/local/lib/R/site-library && \
    R --quiet -e 'if (!require("BiocManager", quietly = TRUE)) install.packages("BiocManager"); BiocManager::install("multtest")' && \
    R -e "install.packages('Seurat', repos='https://cloud.r-project.org')" && \
    R -e "library(Seurat); print('Seurat installed successfully')"


# Ensure R can find Seurat at runtime
ENV R_LIBS_SITE=/usr/local/lib/R/site-library
ENV R_LIBS_USER=/blah

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

