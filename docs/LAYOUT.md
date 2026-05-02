# LAYOUT

This file describes the active unified folder, not the original four source folders.

```text
stock_rtx4060_unified/
├── README.md
├── CHANGELOG.md
├── main.py
├── run.ps1
├── pyproject.toml
├── requirements.txt
├── requirements-gpu-wsl.txt
├── src/stock_rtx4060/
├── tests/
├── docs/
├── examples/
├── reports/
├── review_needed/
├── archive/original_inputs/
├── workspaces/
└── tools/
```

## Folder Purposes

| Path | Purpose |
|---|---|
| `src/stock_rtx4060/` | Active Python package. |
| `tests/` | Regression tests for the unified package. |
| `docs/` | Current user-facing and agent-facing documentation. |
| `reports/` | Consolidation evidence, validation logs, cross-review logs, and runtime output. |
| `review_needed/` | Quarantined source evidence that should not be treated as active docs yet. |
| `archive/original_inputs/` | Placeholder for original input archives if needed later. |
| `workspaces/` | Placeholder only; runtime workspaces were excluded from the executable path. |
| `tools/` | Placeholder only; no standalone maintenance tools are required currently. |

## Current Inventory Counts

| Item | Count |
|---|---:|
| Source files inventoried | 238 |
| Files kept from source roots | 11 |
| Excluded/merged/review-needed candidates | 227 |
| Review-needed files | 4 |
| Duplicate groups | 31 |

## Active Code

Add Python source under `src/stock_rtx4060`.

## Tests

Add tests under `tests`.

## Generated Output

Use `reports/` for validation and runtime output.

Do not promote files from `review_needed/` into active docs without checking command syntax against the current CLI.
