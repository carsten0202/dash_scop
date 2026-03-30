# Repository Guidelines

## Purpose
This repo is a Dash app for visualizing and QC-checking single-cell omics data from Seurat RDS files.

## Architecture
- Keep app startup in `src/app.py`
- Keep CLI entrypoints in `src/cli.py`
- Keep UI structure in `src/layout.py`
- Keep Dash callbacks in `src/callbacks.py`
- Keep reusable helpers in `src/helpers.py`
- Keep config and constants in `src/settings.py`
- Keep R/Seurat loading logic in `src/data_loader.py`

## Style
- Prefer small, focused functions
- Prefer modern Python patterns
- Keep changes minimal and targeted
- Use clear names over clever code
- Avoid unnecessary abstraction
- Prefer refactoring old patterns toward cleaner code when editing nearby files

## Workflow
- Preserve existing behavior unless the change explicitly calls for it
- Do not add compatibility layers unless there is a concrete need
- Keep data-loading, plotting, and UI concerns separated
- Follow repo-local conventions already present in the touched files

## Verification
- Run relevant linting or tests when practical
- Be aware that R and `rpy2` dependencies may limit local verification
- If full verification is not possible, state what was checked and what could not be run

## Cautions
- Do not commit secrets or generated data
- Avoid duplicating config sources unless necessary
- Be careful with large in-memory Seurat data and cache use
