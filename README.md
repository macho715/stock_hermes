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

Observed result after OHLCV cache coverage: 15 tests passed.

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
