# Layout

## Source Tree

```
stock_rtx4060_unified/
├── README.md
├── CHANGELOG.md
├── main.py                      # CLI entry point
├── stock_investment_os.py       # (legacy / reference)
├── run.ps1
├── pyproject.toml               # Project metadata + ruff config
├── requirements.txt             # Core runtime dependencies
├── requirements-openbb.txt      # OpenBB optional dependencies
├── requirements-gpu-wsl.txt     # WSL2/CUDA GPU dependencies
├── requirements-dev.txt         # Development dependencies
├── config/
│   └── data_providers.example.json
├── src/stock_rtx4060/
│   ├── __init__.py
│   ├── main.py                  # CLI parser + command dispatcher
│   ├── recommendation_engine.py # RecommendationEngine orchestrator
│   ├── feature_engine.py        # 60+ technical indicators
│   ├── ensemble_model.py        # XGBoost + LogisticRegression ensemble
│   ├── backtester.py            # Dry-run trade simulation
│   ├── benchmark.py             # Benchmark runner
│   ├── risk_rules.py            # Track-S / Track-L risk gate logic
│   ├── dashboard_bridge.py     # dashboard_snapshot.v1 builder
│   ├── data_providers.py        # yfinance/openbb/synthetic router
│   ├── provider_validation.py   # point-in-time OHLCV provider checks
│   ├── hw_profile.py            # GPU detection (nvidia-smi)
│   ├── audit_log.py             # Masked JSONL audit writer
│   ├── ops_workflow.py          # Ops v1 daily brief + manual approval
│   ├── mcp_adapter.py           # Phase 1 read/report-only MCP adapter
│   └── reports.py               # Shared Markdown/JSON/CSV helpers
├── dashboard/
│   ├── stock_pred_v5.jsx        # Repo-owned dashboard source copy
│   ├── bridge_smoke.html
│   └── verify_bridge_smoke.mjs
├── tests/
│   ├── test_core.py             # Ops v1 workflow regression tests
│   ├── test_data_providers.py   # Provider routing tests
│   ├── test_provider_validation.py # Provider validation tests
│   ├── test_audit_log.py        # Audit masking tests
│   ├── test_mcp_adapter.py      # MCP boundary tests
│   └── test_dashboard_bridge.py # Dashboard bridge tests
├── docs/
│   ├── LAYOUT.md                # This file — source tree + conventions
│   ├── SYSTEM_ARCHITECTURE.md   # Architecture overview
│   ├── SPEC.md                 # Algorithm specification
│   ├── SETUP.md                # Setup guide
│   ├── AGENTS.md               # Agent-facing project guidance
│   ├── UIUX.md                 # UI/UX design notes
│   ├── REPORTS_POLICY.md       # Report output policy
│   └── plan*.md / SPEC*.md     # Feature plans and specs
├── .continue/checks/           # Flat Continue PR-quality check files
│   ├── 01-financial-safety-boundary.md
│   ├── 02-backtest-integrity.md
│   ├── 03-recommendation-contract.md
│   ├── 04-secret-and-pii-safety.md
│   ├── 05-gpu-claim-validation.md
│   ├── 06-report-contract.md
│   ├── 07-architecture-boundary.md
│   └── 08-test-and-verification.md
├── examples/
├── reports/                     # Runtime output + validation logs
├── review_needed/              # Quarantined source evidence (not active docs)
├── archive/original_inputs/    # Archive of original inputs
├── workspaces/
└── tools/
```

## Active Package Modules

`src/stock_rtx4060/` — all active Python source.

| File | Purpose |
|---|---|
| `main.py` | CLI argument parser and command dispatcher (`recommend`, `benchmark`, `ops-v1`, `env`, `dashboard-export`). |
| `recommendation_engine.py` | `RecommendationEngine` — candidate scoring, OHLCV caching, report generation. |
| `feature_engine.py` | 60+ technical indicators: SMA, EMA, RSI, MACD, ATR, Bollinger, volume delta, etc. |
| `ensemble_model.py` | XGBoost + LogisticRegression ensemble with OOF CV, `TimeSeriesSplit(gap=horizon)`. |
| `backtester.py` | Dry-run trade simulation: entry/exit logic, P&L, Sharpe, MDD. |
| `benchmark.py` | Benchmark smoke runner. |
| `risk_rules.py` | Track-S / Track-L risk gate rules: stop, take-profit, risk budget, position cap. |
| `dashboard_bridge.py` | Converts recommendation JSON into `dashboard_snapshot.v1` for frontend file import. |
| `data_providers.py` | OHLCV provider router: `auto`, `synthetic`, `yfinance`, optional `openbb`. |
| `provider_validation.py` | Point-in-time OHLCV checks for row count, date range, duplicate/future rows, required columns, nulls, and freshness evidence. |
| `hw_profile.py` | GPU detection via `nvidia-smi`; device selection and VRAM logging. |
| `audit_log.py` | Masked JSONL audit event writer; provider attempt events. |
| `ops_workflow.py` | Ops v1 daily brief, manual approval template, ZERO log, summary generation. |
| `mcp_adapter.py` | Phase 1 read/report-only MCP adapter contract. Does not start an MCP server. |
| `reports.py` | Shared Markdown, JSON, CSV report helpers. |

## File Naming Conventions

- Python modules: `snake_case` (`recommendation_engine.py`, `feature_engine.py`, `risk_rules.py`)
- Entry point: `main.py` (root-level CLI dispatcher)
- Benchmark: `benchmark.py`
- API / preview: `api_server.py`, `preview_server.py` (root-level if present)
- Recommendation configs: `RecommendationConfig` dataclass defined in `recommendation_engine.py`

## Configuration Files

| File | Controls | Format |
|---|---|---|
| `requirements.txt` | Core runtime dependencies | pip |
| `requirements-openbb.txt` | OpenBB optional provider | pip |
| `requirements-gpu-wsl.txt` | WSL2/CUDA GPU deps | pip |
| `requirements-dev.txt` | Development deps | pip |
| `pyproject.toml` | Project metadata + ruff config | TOML |
| `config/data_providers.example.json` | Non-secret provider config example | JSON |
| `.env` (optional, not committed) | API keys, debug flags | key=val |

## Key Entry Points

| Entry | Command | Purpose |
|---|---|---|
| `main.py` | `python main.py --recommend --universe AAPL --track S` | Run recommendation scan |
| `main.py` | `python main.py --benchmark --synthetic --benchmark-rows 1200` | Benchmark smoke test |
| `main.py` | `python main.py --recommend --synthetic --universe SYNTH-A --track BOTH --top 5 --output-dir reports` | Offline smoke |
| `main.py` | `python main.py --recommend --universe AAPL,MSFT,NVDA --track BOTH --period 3y --top 5` | Live yfinance scan |
| `main.py` | `python main.py --ticker AAPL --period 5y --horizon 5` | Single-ticker pipeline |
| `main.py` | `python main.py --ops-v1` | Ops v1 manual approval workflow |
| `main.py` | `python main.py --dashboard-export --output-dir reports` | Dashboard snapshot export |
| `main.py` | `python main.py --env` | Runtime environment status |
| `preview_server.py` | `python preview_server.py` | Flask + Vite unified launcher |
| `api_server.py` | `python api_server.py --port 5151` | Flask API server |

## Generated Output

| Pattern | Source command |
|---|---|
| `reports/recommendations*/` | `recommend` smoke / live runs |
| `reports/ops_v1*/` | `ops-v1` manual approval workflow runs |
| `reports/runtime_status.json` | `env` command |
| `reports/**/audit_log.jsonl` | Provider attempt audit events from `recommend` and `ops-v1` |
| `reports/**/dashboard_snapshot.json` | Dashboard bridge snapshot from `dashboard-export`, including additive `provider_summary` when present |

## Continue Checks

Flat checks under `.continue/checks/`. Do not create nested folders. Current set:

- `01-financial-safety-boundary.md`
- `02-backtest-integrity.md`
- `03-recommendation-contract.md`
- `04-secret-and-pii-safety.md`
- `05-gpu-claim-validation.md`
- `06-report-contract.md`
- `07-architecture-boundary.md`
- `08-test-and-verification.md`

## External Dashboard File

`C:\Users\jichu\Downloads\주식\stock_pred_v5.jsx` is the live dashboard. It imports `dashboard_snapshot.v1` files via a `BACKEND` button and shows backend evidence in a dedicated tab.

The repo-owned copy is at `dashboard/stock_pred_v5.jsx` so dashboard source changes are tracked by repo `git status`.

## Reports Policy

See `docs/REPORTS_POLICY.md` for distinguishing review evidence from generated runtime output. Existing report files must not be deleted without explicit approval.
