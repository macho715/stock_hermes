# Changelog

All notable changes to `stock_rtx4060_unified` are documented here.

## [Unreleased]

### Added

- Created unified executable folder at `stock_rtx4060_unified` on 2026-05-02 20:53:47.
- Added `src/stock_rtx4060` as the single active package location.
- Added consolidation audit reports under `reports/`.

### Changed

- Selected the validated active package from `workspaces/stock_rtx4060` over raw bundle and patch variants.
- Patched root `main.py`, `pyproject.toml`, and tests for `src` layout.
- Normalized docs into root `README.md`, root `CHANGELOG.md`, and `docs/`.

### Removed From Runtime Path

- Exact duplicate bundle files.
- Python cache files.
- Generated benchmark/recommendation reports from source folders.
- Superseded raw patch source variants.

### Security

- No broker execution path was added.
- Source folders were not deleted.
