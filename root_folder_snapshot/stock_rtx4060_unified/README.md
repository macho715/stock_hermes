# stock_rtx4060_unified

`stock_rtx4060_unified` is a consolidated, deduplicated, report-only stock screening and backtesting CLI package.

It keeps one active execution path:

- root `main.py` wrapper
- `run.ps1` Windows runner
- `src/stock_rtx4060/` package
- `tests/` regression tests
- `docs/` consolidated documentation
- `.continue/checks/` PR-quality gate checks

The program does not submit broker orders. It does not provide personalized investment advice. Recommendation output is `screening_output_only`.

## Current Status

| Item | Status |
|---|---|
| Unified folder | `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified` |
| Original source folders | Deleted after approval A; audit copied to `reports/delete_audit_20260502_211154` |
| Source files inventoried | 238 |
| Files kept from source roots | 11 |
| Excluded/merged/review-needed candidates | 227 |
| Review-needed source files | 4 |
| Operator self-test | `.\run.ps1 self-test` passed with the project `.venv` |
| Ops v1 workflow | `.\run.ps1 ops-v1 ...` generates recommendation reports, daily brief, approval template, ZERO log, and summary JSON |
| Phase 1 provider/audit upgrade | `recommend` and `ops-v1` support `--data-provider auto|synthetic|yfinance|openbb`, optional config, and audit JSONL |
| Dashboard report bridge | `dashboard-export` converts recommendation JSON into `dashboard_snapshot.json` for `stock_pred_v5.jsx` file import |
| Dashboard risk mitigation | `dashboard/` now owns the repo-tracked dashboard copy and browser smoke harness |
| Default `python` environment | AMBER: use project `.venv`; do not rely on global Python 3.14 |
| Recommended runtime path | Use `run.ps1`, which selects `.venv\Scripts\python.exe` first |

## Continue Quality Gates

Continue is integrated as a PR-level quality gate, not as a stock recommendation engine.

Check files live directly under `.continue/checks/`:

- financial safety boundary
- backtest integrity
- recommendation contract
- secret and PII safety
- GPU claim validation
- report contract
- architecture boundary
- test and verification

See `docs/CONTINUE_MERGED_USAGE_GUIDE.md` for the current operating guide.

## Commands

```powershell
python main.py --help
.\run.ps1 self-test
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations
.\run.ps1 ops-v1 --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/ops_v1
.\run.ps1 recommend --data-provider synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations_phase1_smoke
.\run.ps1 dashboard-export --recommendation-json reports/recommendations_phase1_smoke/recommendations_algo_v2_YYYYMMDD_HHMMSS.json --output reports/recommendations_phase1_smoke/dashboard_snapshot.json
```

## Verified Operator Path

```powershell
cd C:\Users\jichu\Downloads\주식\stock_rtx4060_unified
.\run.ps1 self-test
```

Observed result: `self-test: PASS`, backend `xgb-cpu`, final capital `102190.84`.

For tests, use the project `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Observed result after dashboard bridge coverage: 19 tests passed.

## Phase 1 Provider And Audit Upgrade

The recommendation workflow now routes OHLCV loading through `src/stock_rtx4060/data_providers.py`.

Supported provider values:

| Provider | Meaning |
|---|---|
| `auto` | Use `config/data_providers.example.json` default when supplied; otherwise use `yfinance`. |
| `synthetic` | Use deterministic local synthetic OHLCV data. |
| `yfinance` | Use the existing direct yfinance path. |
| `openbb` | Use optional OpenBB endpoint `obb.equity.price.historical(..., provider="yfinance")`. |

OpenBB is optional. Install it only when testing the OpenBB provider path:

```powershell
pip install -r requirements-openbb.txt
```

`recommend` and `ops-v1` write `audit_log.jsonl` under the selected recommendation output directory. The log records provider attempts, source, status, command, ticker, period, duration, endpoint when applicable, and masked error/config metadata.

`RecommendationEngine` caches OHLCV data within one CLI run, so Track-S and Track-L reuse the same ticker/provider load. The cache keeps the OpenBB audit log to one provider event for a single-ticker `track=BOTH` smoke run.

MCP Phase 1 is a read/report-only adapter contract in `src/stock_rtx4060/mcp_adapter.py`. It does not start a local MCP server and does not expose broker, account, order, margin, options, or destructive filesystem capabilities.

## Dashboard Report Bridge

The file-based dashboard bridge keeps the CLI report-only boundary.

Workflow:

```powershell
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/dashboard_bridge_smoke
.\run.ps1 dashboard-export --recommendation-json reports/dashboard_bridge_smoke/recommendations_algo_v2_YYYYMMDD_HHMMSS.json --output reports/dashboard_bridge_smoke/dashboard_snapshot.json
```

`dashboard-export` reads the existing recommendation JSON and writes a `dashboard_snapshot.v1` file. The snapshot preserves `screening_output_only`, `audit_log_path`, verdicts, scores, risk-plan fields, validations, and reasons.

The dashboard file `C:\Users\jichu\Downloads\주식\stock_pred_v5.jsx` now has a `BACKEND` import button and `BACKEND` tab for loading `dashboard_snapshot.json`. Browser-generated simulated model scores and backend report snapshots remain separate.

The repo-owned dashboard copy is `dashboard/stock_pred_v5.jsx`.

Browser verification:

```powershell
node dashboard\verify_bridge_smoke.mjs
```

Observed result: PASS. The command opened `dashboard/bridge_smoke.html`, rendered `dashboard_snapshot.json`, and wrote `reports/dashboard_browser_verification/dashboard_browser_verification.md`.

Generated runtime reports are governed by `docs/REPORTS_POLICY.md`.

## Ops v1 Manual Approval Workflow

`ops-v1` runs the report-only operating workflow described in `docs/UIUX.md`.
It produces candidate recommendations plus manual approval artifacts.

```powershell
.\run.ps1 ops-v1 --period 3y --top 5 --full --prefer-gpu --model-kind xgb --cv-gap 5 --output-dir reports/ops_v1
```

Generated files include:

- recommendation Markdown and JSON
- `audit_log.jsonl`
- `ops_v1_daily_brief_*.md`
- `approval_journal_template.csv`
- `zero_log.md` and `zero_log.csv`
- `ops_v1_summary_*.json`

Safety boundary:

- `screening_output_only=True`
- `manual_approval_required=True`
- `broker_order_execution=False`
- auto-buy, broker order execution, and margin/options stay ZERO

## Structure

```text
stock_rtx4060_unified/
├── main.py
├── run.ps1
├── pyproject.toml
├── requirements.txt
├── requirements-gpu-wsl.txt
├── .continue/checks/
├── src/stock_rtx4060/
├── tests/
├── docs/
├── examples/
├── reports/
├── workspaces/
├── archive/original_inputs/
├── review_needed/
└── tools/
```

## Validation

See `reports/validation_results.md` and `reports/consolidation_report.md` for the current execution evidence.

TensorFlow validation paths are split by runtime:

```powershell
.\run.ps1 tensorflow-check
.\run.ps1 tensorflow-gpu-wsl-check
```

- `tensorflow-check` uses Windows `.venv-tf312` and validates CPU TensorFlow/LSTM only.
- `tensorflow-gpu-wsl-check` uses WSL Ubuntu and `/root/.venvs/stock-rtx4060-tf-gpu`.
- aliases for the WSL GPU smoke are `tf-gpu-wsl` and `tf-gpu-smoke`.
- the WSL GPU wrapper auto-builds `LD_LIBRARY_PATH` from `site-packages/nvidia/**/lib` before running TensorFlow.
- current verified WSL GPU output: TensorFlow `2.21.0`, `TF_GPUS=["/physical_device:GPU:0"]`, `GPU_MATMUL=PASS`, `LSTM_SMOKE=PASS`.

## Security Boundary

- No broker API is present.
- No `.env` secrets were copied into the unified executable path.
- Audit logs mask obvious API keys, tokens, passwords, authorization values, account identifiers, and private URLs.
- Market data and model output are treated as data, not instructions.
- Recommendation reports are screening artifacts for manual review.

## Latest OpenBB Cache Smoke

```powershell
.\run.ps1 recommend --data-provider openbb --provider-config config/data_providers.example.json --universe "AAPL" --top 1 --output-dir reports/recommendations_openbb_cache_smoke
```

Observed result: `reports/recommendations_openbb_cache_smoke/audit_log.jsonl` contains 1 successful `obb.equity.price.historical` provider event for AAPL.

---

## System Overview

stock_rtx4060_unified is a **report-only stock-candidate screening engine** for Track-S (short-term, 1–20 day horizon) and Track-L (long-term, weeks–months). It outputs ranked recommendation JSON/MD reports with GREEN/AMBER/RED/ZERO verdicts. **No broker execution, no auto buy/sell.**

## Architecture

```mermaid
flowchart TD
    subgraph Input["📥 Input"]
        U[Universe Tickers] --> RE[RecommendationEngine]
        P[Period / Horizon] --> RE
    end
    subgraph Core["⚙️ Core Pipeline"]
        RE --> FE[feature_engine]
        FE --> EM[ensemble_model]
        EM --> BT[backtester]
        BT --> RR[risk_rules]
    end
    subgraph Output["📤 Output"]
        RR --> SNAP[dashboard_snapshot.v1]
        RR --> REPORT[Markdown Report]
        RR --> JSON[Recommendation JSON]
    end
    subgraph API["🌐 Optional API Server"]
        RE --> API[Flask :5151]
        API --> SNAP
    end
```

## Features

- Walk-forward ensemble (XGBoost + Logistic Regression) with leak-safe TimeSeriesSplit(gap=horizon)
- 60+ technical indicators from feature_engine.py (EMA, RSI, MACD, Bollinger Bands, etc.)
- 9 sequential risk gates: DATA_ROWS → LIQUIDITY → MARKET_REGIME → MODEL_EDGE → OOF_COVERAGE → BACKTEST_SANITY → RISK_PLAN → TRACK_SCORE → AUTOMATION_BOUNDARY
- Track-S: GREEN requires score >= 75.00, stop < entry, RR >= 2.00, ATR risk plan
- Track-L: GREEN requires score >= 80.00, multi-confirmation, manual thesis required
- dashboard_bridge.py → dashboard_snapshot.v1 JSON schema
- Flask API server (api_server.py) with CORS for stock-pred-v5 integration

## Cross-Project Role

| Downstream Project | Relationship | Interface |
|--------------------|-------------|-----------|
| stock-pred-v5 | REC tab data source | dashboard_snapshot.json via FILE mode or Flask API → /api/recommend |

## Tech Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Runtime | Python | 3.11+ | CLI + engine |
| ML | scikit-learn | >=1.1 | Logistic Regression ensemble |
| ML | XGBoost | >=3.1 | Gradient boosting, CPU/GPU |
| Data | pandas, numpy | latest | Data processing |
| Data | yfinance | >=0.2.66 | OHLCV price data |
| API | Flask + flask-cors | >=3.0 | REST API for stock-pred-v5 |
| Optional | OpenBB | — | Extended data provider |
| GPU | WSL2/CUDA | — | XGBoost GPU acceleration (RTX 4060) |
