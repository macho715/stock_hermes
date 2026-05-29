# Contributing Guide

_Source of truth: `pyproject.toml`, `requirements*.txt`, `run.ps1`, `main.py`_
_Last synced: 2026-05-07_

---

## Development Environment Setup

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12 (recommended) or 3.11 | Use `.venv` inside the repo, not global Python |
| Git | any | |
| PowerShell | 5.1+ | Required for `run.ps1` wrapper |

> **Warning:** The global `python` on this machine may be Python 3.14. Always use the project `.venv`.

### First-Time Setup

```powershell
cd C:\Users\jichu\Downloads\주식\stock_rtx4060_unified

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
python main.py self-test
```

Expected output: `self-test: PASS`

### Optional Providers

| File | When to install |
|------|----------------|
| `requirements-openbb.txt` | Validating `--data-provider openbb` |
| `requirements-gpu-wsl.txt` | TensorFlow LSTM on WSL2/CUDA GPU (Linux only) |

```powershell
pip install -r requirements-openbb.txt     # OpenBB path
# For GPU: run inside WSL2 Ubuntu
pip install -r requirements-gpu-wsl.txt
```

---

## Available Commands

All commands are run through `run.ps1` (wraps `.venv\Scripts\python.exe main.py`):

```powershell
.\run.ps1 <subcommand> [args]
```

### Core Subcommands (`main.py`)

| Subcommand | Description |
|-----------|-------------|
| `self-test` | Internal smoke tests — default when no args given |
| `env` | Validate runtime/GPU environment |
| `benchmark` | Run synthetic CPU/GPU benchmark |
| `predict` | Train/predict from CSV or yfinance |
| `recommend` | Rank report-only Track-S/Track-L candidates |
| `report` | Generate Daily Brief / Risk Dashboard reports |
| `paper-run` | Paper-only virtual trading (no broker orders, screening only) |
| `ops-v1` | Report-only Ops v1 workflow with manual approval artifacts |
| `dashboard-export` | Convert recommendation JSON to dashboard snapshot |
| `demo` | Create sample data and reports |
| `journal` | Append decision journal row |

### TensorFlow Wrapper Subcommands (`run.ps1`)

| Alias | Description |
|-------|-------------|
| `tensorflow-check` / `tf-check` / `tf-smoke` | Validate Windows-native TF 2.x CPU LSTM |
| `tensorflow-gpu-wsl-check` / `tf-gpu-wsl` / `tf-gpu-smoke` | Validate TF GPU inside WSL2/CUDA |

### Common Usage Examples

```powershell
# Smoke test (synthetic data, offline)
.\run.ps1 recommend --data-provider synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --output-dir reports/smoke

# Real yfinance scan
.\run.ps1 recommend --universe AAPL,MSFT,NVDA,QQQ,SPY --track BOTH --period 3y --top 5

# Track-S only with XGBoost GPU attempt
.\run.ps1 recommend --universe AAPL,NVDA,QQQ --track S --period 3y --top 5 --model-kind auto --xgb-device cuda

# Run full benchmark
.\run.ps1 benchmark --synthetic --benchmark-rows 1200 --universe SYNTH-A --output-dir reports

# Export dashboard snapshot
.\run.ps1 dashboard-export
```

---

## Data Provider Config

Copy the example config and customize:

```powershell
copy config\data_providers.example.json config\data_providers.json
```

`config/data_providers.example.json`:
```json
{
  "default_provider": "yfinance",
  "openbb_provider": "yfinance"
}
```

Provider priority order: `pykrx` (KRX symbols) → `FinanceDataReader` (fallback) → `yfinance` → `openbb` → `synthetic`

KRX symbols are detected by `.KS` or `.KQ` suffix.

Data cache is controlled by `USE_DATA_CACHE` env var (default: `"1"` = enabled). Set `USE_DATA_CACHE=0` to bypass the SQLite cache.

---

## Testing

### Run Tests

```powershell
# Fast (quiet)
.\.venv\Scripts\python.exe -m pytest -q

# With coverage
.\.venv\Scripts\python.exe -m pytest --cov=stock_rtx4060 --cov-report=term-missing -q
```

### Coverage Requirements

| Threshold | Target | Current |
|-----------|--------|---------|
| Minimum (`fail_under`) | 75% | ~81% |
| Goal | 80%+ | ✓ |

Coverage configuration in `pyproject.toml`:
- **Source:** `src/stock_rtx4060`
- **Branch coverage:** enabled
- **Excluded:** `hw_profile.py`, `benchmark.py` (hardware-dependent)

### Test Structure

```
tests/
├── test_algorithm_v2.py          # Core algorithm integration tests
├── test_data_providers_extra.py  # data_providers.py coverage (42 tests)
├── test_reports.py               # reports.py formatting (35 tests)
├── test_risk_rules.py            # risk_rules.py (66 tests)
└── ...
```

### TDD Workflow

1. Write failing test (RED)
2. Implement minimal code (GREEN)
3. Refactor (IMPROVE)
4. Verify: `pytest -q` passes, coverage ≥ 75%

---

## Code Conventions

| Setting | Value |
|---------|-------|
| Line length | 120 |
| Target Python | 3.12 compatible syntax |
| Formatter | black (`line-length = 120`) |
| Linter | ruff (`E`, `F`, `I`, `UP`, `B`; `E501` ignored) |

### Linting

```powershell
.\.venv\Scripts\python.exe -m ruff check src/ tests/
.\.venv\Scripts\python.exe -m black --check src/ tests/
```

### Key Invariants

- **No broker execution** — `screening_output_only=True` must remain in all recommendation result objects
- **No mutation** — use spread/copy patterns, do not mutate shared state
- **Leak-safe CV** — use PurgedKFold/embargo OOF probabilities; never in-sample probabilities
- **Risk Gate is mandatory** — model probability alone cannot produce a GREEN verdict
- **Manual approval required** before any external write, credential handling, or deployment

---

## CI / GitHub Actions

Workflow: `.github/workflows/ci.yml`

| Trigger | Action |
|---------|--------|
| Push to `main` / `master` | Run tests with coverage |
| Pull request | Run tests with coverage |

Steps: checkout → Python 3.12 → `pip install -r requirements.txt pytest pytest-cov` → `pytest --cov=stock_rtx4060 --cov-report=xml` → upload `coverage.xml` artifact → Codecov upload

---

## Modules Overview

| Module | Purpose |
|--------|---------|
| `data_providers.py` | OHLCV loading: yfinance, pykrx, FDR, OpenBB, synthetic |
| `data_cache.py` | SQLite-backed OHLCV cache |
| `feature_engine.py` | Technical indicator feature generation |
| `ensemble_model.py` | XGBoost/LSTM model training and OOF prediction |
| `backtester.py` | Walk-forward backtesting and Kelly sizing |
| `backtest_honesty.py` | Anti-lookahead and OOF coverage checks |
| `risk_rules.py` | Position sizing, gate evaluation, Track-S/L scoring |
| `recommendation_engine.py` | Candidate ranking and verdict generation |
| `reports.py` | Markdown/CSV/JSON report writing |
| `ops_workflow.py` | Ops v1 workflow orchestration |
| `paper_trading.py` | Virtual paper trading (no broker connection) |
| `alert_engine.py` | Threshold-based alert generation |
| `position_tracker.py` | Open position tracking |
| `portfolio_analytics.py` | Portfolio-level metrics |
| `trade_journal.py` | Decision journal persistence |
| `broker_bridge.py` | Adapter stub — no live order execution |
| `dashboard_bridge.py` | Dashboard JSON export |
| `audit_log.py` | JSONL audit trail for provider selections |
| `provider_validation.py` | Data quality gate checks |
| `validation_gates.py` | Recommendation validation gates |
| `krx_calendar.py` | KRX trading calendar utilities |
| `kevpe_adapter.py` | KEPCO/external adapter |
| `mcp_adapter.py` | MCP integration adapter contract |
| `journal.py` | Append-only decision journal |
