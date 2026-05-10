# PATCH_NOTES

The unified package keeps the active integrated Algorithm v2 implementation under `src/stock_rtx4060`. Older patch copies are recorded in inventory and excluded or marked review-needed.

## 2026-05-10 — Hedge-Fund Grade Upgrade (P0–P8 completion)

| Area | Change |
|------|--------|
| Coverage | 78.5% → **85.82%** (1,210 tests); target ≥85% met |
| CORS | `api_server.py` changed from `origins=["*"]` to explicit localhost origins (5173, 4173, 5151) |
| `logging.basicConfig` | `InterceptHandler` isolation fix; tests use `monkeypatch` to avoid global handler |
| P0 Observability | `src/stock_rtx4060/observability/` — loguru JSONL, prometheus_client, MLflow wrappers |
| P1 Data Lake | `src/stock_rtx4060/data_lake/` — DuckDB+Parquet PITStore, bitemporal `as_of`, KIS/Alpaca ingestors |
| P2 Factors | `src/stock_rtx4060/factors/` — Alpha101/158, Barra cross-sectional, RD-Agent runner |
| P3 ML | `src/stock_rtx4060/ml/` — PurgedKFold, Optuna HPO, MLflow tracking, SHAP |
| P4 Portfolio | `src/stock_rtx4060/portfolio/` — skfolio HRP/NCO/CVaR, BL views, turnover cost |
| P5 Backtest | `src/stock_rtx4060/backtest/` — vectorbt sweep, MC bootstrap, Deflated Sharpe/PSR |
| P6 LLM Advisor | `src/stock_rtx4060/advisors/` — NewsSentiment, DevilsAdvocate, MacroRegime, LangGraph |
| P7 Orchestration | `flows/daily_krx.py`, `flows/daily_us.py`, `flows/research_weekly.py` — Prefect 3 |
| P8 Brokers | `src/stock_rtx4060/broker/` — Alpaca/IBKR/KIS adapters, OrderRouter, kill-switch |
| Key commits | `717f3a0` (coverage/CORS/InterceptHandler), `c6f0928` (utcnow×6, parse_args), `d1f5a9a` (numpy read-only) |

## 2026-05-08 — Test Suite Expansion (509 tests, 89%)

| Area | Change |
|------|--------|
| Tests | 340 → 509 tests; coverage 80.79% → 89% |
| `ensemble_model.py` | 49% → 83% via `test_ensemble_model_extra.py` (50 tests) |
| `kevpe_adapter.py` | 43% → 91% via `test_kevpe_adapter.py` (57 tests) |
| `main.py` | 51% → 98% via `test_main_extra.py` (61 tests) |
| Docs | Added `docs/CONTRIB.md`, `docs/RUNBOOK.md`, `docs/PHASE1_GAP_ANALYSIS_2026-05-07.md` |

## Current Patch State

| Item | Decision |
|---|---|
| Active code source | Kept from the integrated workspace package. |
| Legacy recommendation patch docs | Moved to `review_needed/` when command syntax did not match the active CLI. |
| Bundle duplicates | Excluded from the unified executable path when exact duplicates were detected. |
| Runtime outputs | Excluded unless needed as generated validation evidence under `reports/`. |
| Original source folders | Deleted after approval A; audit copied to `reports/delete_audit_20260502_211154`. |
| Ops v1 workflow | Added as `src/stock_rtx4060/ops_workflow.py` and exposed through `.\run.ps1 ops-v1 ...`. |
| Dashboard report bridge | Added as `src/stock_rtx4060/dashboard_bridge.py` and exposed through `.\run.ps1 dashboard-export ...`. |

## Latest Documentation Sync

The active docs now reflect the post-consolidation validation split:

- `.\run.ps1 self-test` passed with the project `.venv`.
- `.venv\Scripts\python.exe -m pytest -q` passed with 19 tests after dashboard bridge integration.
- `.\run.ps1 ops-v1 --universe "AMZN,AAPL" ...` generated recommendation reports, daily brief, approval journal template, ZERO logs, and summary JSON with `error_count=0`.
- `.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" ...` generated Markdown, JSON, and `audit_log.jsonl`.
- `.\run.ps1 recommend --data-provider openbb --provider-config config/data_providers.example.json --universe "AAPL" ...` generated `reports/recommendations_openbb_cache_smoke/audit_log.jsonl` with 1 provider event.
- `.\run.ps1 dashboard-export --recommendation-json ... --output reports/dashboard_bridge_smoke/dashboard_snapshot.json` generated a `dashboard_snapshot.v1` file for `stock_pred_v5.jsx` import.
- Global Python 3.14 remains AMBER; project execution should use `.venv`.
