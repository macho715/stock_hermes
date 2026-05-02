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
├── requirements-openbb.txt
├── requirements-gpu-wsl.txt
├── config/
│   └── data_providers.example.json
├── .continue/
│   └── checks/
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
| `config/` | Non-secret example runtime config. Current file: `data_providers.example.json`. |
| `.continue/checks/` | Flat Continue check files for PR-quality review. |
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

Important active modules:

| File | Purpose |
|---|---|
| `main.py` | CLI parser and command dispatcher. |
| `recommendation_engine.py` | Report-only candidate scoring, per-run OHLCV cache, and recommendation reports. |
| `data_providers.py` | OHLCV provider router for `auto`, `synthetic`, `yfinance`, and optional `openbb`. |
| `audit_log.py` | Masked JSONL audit event writer. |
| `mcp_adapter.py` | Phase 1 read/report-only MCP adapter contract. It does not start an MCP server. |
| `ops_workflow.py` | Ops v1 daily brief, manual approval template, ZERO log, and summary generation. |
| `reports.py` | Shared Markdown/JSON/CSV report helpers. |
| `risk_rules.py` | Track-S / Track-L risk rules. |

## Continue Checks

Add or update Continue checks only under `.continue/checks/`.

Do not create nested check folders. The current check set is:

- `01-financial-safety-boundary.md`
- `02-backtest-integrity.md`
- `03-recommendation-contract.md`
- `04-secret-and-pii-safety.md`
- `05-gpu-claim-validation.md`
- `06-report-contract.md`
- `07-architecture-boundary.md`
- `08-test-and-verification.md`

## Tests

Add tests under `tests`.

Ops v1 workflow behavior is covered in `tests/test_core.py`.
Provider routing, audit masking, and MCP boundary checks are covered in:

- `tests/test_data_providers.py`
- `tests/test_audit_log.py`
- `tests/test_mcp_adapter.py`

## Generated Output

Use `reports/` for validation and runtime output.

Current runtime output families include:

| Pattern | Source command |
|---|---|
| `reports/recommendations*/` | `recommend` command smoke/live runs. |
| `reports/ops_v1*/` | `ops-v1` manual approval workflow runs. |
| `reports/runtime_status.json` | `env` command. |
| `reports/**/audit_log.jsonl` | Provider attempt audit events from `recommend` and `ops-v1`. |

Do not promote files from `review_needed/` into active docs without checking command syntax against the current CLI.
