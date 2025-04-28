# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.13.1
FROM debian:trixie-20250317-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV GNUMAKEFLAGS=-j5

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    libcairo2-dev \
    libcurl4-openssl-dev \
    libfftw3-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    libjpeg-dev \
    libpng-dev \
    libssl-dev \
    libtiff5-dev \
    libxml2-dev \
    python3-pip \
    python3.13-venv \
    r-base 

#  libudunits2-dev


# Install Seurat and dependencies
RUN mkdir -p /usr/local/lib/R/site-library && chmod -R 777 /usr/local/lib/R/site-library
RUN R --quiet -e 'if (!require("BiocManager", quietly = TRUE)) install.packages("BiocManager"); BiocManager::install("multtest")' && \
    R --quiet -e "install.packages('Seurat', repos='https://cloud.r-project.org', quiet=TRUE)"


# Ensure R can find Seurat at runtime
ENV R_LIBS_SITE=/usr/local/lib/R/site-library


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
RUN python3 -m venv .venv
RUN .venv/bin/python3 -m pip install --upgrade pip && \
    .venv/bin/python3 -m pip install -r requirements.txt

COPY testdata/seurat_obj_downsampled.rds data/data.rds
COPY src .

# Expose and run
EXPOSE 8050
CMD ["/app/.venv/bin/python3", "/app/cli.py", "--ip", "0.0.0.0", "--port", "8050", "--rds", "/app/data/data.rds"]

