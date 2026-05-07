# Operations Runbook

_Source of truth: `run.ps1`, `main.py`, `config/runtime_environment.json`_
_Last synced: 2026-05-07_

> **Scope:** All procedures are report-only / screening-only.
> This system does not execute broker orders, manage accounts, or perform live trades.

---

## Runtime Environment

| Item | Value |
|------|-------|
| Runtime lock | `config/runtime_environment.json` |
| Python | `.venv\Scripts\python.exe` (3.12) |
| Test command | `.venv\Scripts\python.exe -m pytest` |
| Compile check | `.venv\Scripts\python.exe -m compileall` |

---

## Daily Operations

### 1. Smoke Test (offline, no network required)

```powershell
.\run.ps1 self-test
```

Expected: `self-test: PASS`

### 2. Daily Recommendation Run (yfinance)

```powershell
.\run.ps1 recommend --universe AAPL,MSFT,NVDA,QQQ,SPY --track BOTH --period 3y --top 5
```

Outputs land in `recommendation_reports/` (Markdown + JSON).

### 3. Generate Reports

```powershell
.\run.ps1 report
```

Outputs: Daily Brief (`reports/daily_brief_*.md`), Risk Dashboard (`reports/risk_dashboard_*.md`).

### 4. Paper Trading Run

```powershell
.\run.ps1 paper-run
```

No broker connection. All fills are virtual. Output is screening evidence only.

---

## Environment Validation

### CPU/GPU Hardware Check

```powershell
.\run.ps1 env
```

### XGBoost GPU Attempt

```powershell
.\run.ps1 recommend --universe AAPL,NVDA --track S --period 3y --top 2 --model-kind auto --xgb-device cuda
```

XGBoost GPU requires RTX 4060 with CUDA drivers installed. Falls back to CPU if unavailable.

### TensorFlow (Windows CPU)

```powershell
.\run.ps1 tf-check
```

Requires `.venv-tf312` venv (separate from `.venv`):
```powershell
py -3.12 -m venv .venv-tf312
.\.venv-tf312\Scripts\python.exe -m pip install tensorflow
.\run.ps1 tf-check
```

> TensorFlow GPU is NOT supported on Windows Native after TF 2.10. Use WSL2 path instead.

### TensorFlow GPU (WSL2/CUDA)

```powershell
.\run.ps1 tf-gpu-wsl
```

Environment variables (optional overrides):

| Variable | Default | Description |
|----------|---------|-------------|
| `STOCK_TF_WSL_DISTRO` | `Ubuntu` | WSL2 distro name |
| `STOCK_TF_WSL_PYTHON` | `/root/.venvs/stock-rtx4060-tf-gpu/bin/python` | Python path in WSL2 |
| `STOCK_TF_WSL_NVIDIA_ROOT` | `/root/.venvs/stock-rtx4060-tf-gpu/lib/python3.12/site-packages/nvidia` | NVIDIA lib root |

---

## Common Issues and Fixes

### `ModuleNotFoundError` on startup

```
Missing Python package: <name>
```

**Fix:**
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py self-test
```

If the error mentions `yfinance` and `USE_DATA_CACHE=1`, the SQLite cache may be stale:
```powershell
$env:USE_DATA_CACHE = "0"
.\run.ps1 recommend --universe AAPL --track S --period 1y --top 1
```

---

### `No Python runtime found` from `run.ps1`

**Fix:** Ensure `.venv` exists in the project root:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

### `yfinance` rate limit / connection error

```
YFRateLimitError / ConnectionError
```

**Fix (use synthetic data for smoke test):**
```powershell
.\run.ps1 recommend --data-provider synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --output-dir reports/smoke
```

**Fix (use OpenBB with cache):**
```powershell
.\run.ps1 recommend --data-provider openbb --provider-config config/data_providers.json --universe AAPL --top 1 --output-dir reports/smoke
```

---

### pykrx failure for KRX symbols (`.KS` / `.KQ`)

pykrx → FinanceDataReader fallback is automatic. If both fail:

```powershell
# Verify FDR is installed
.\.venv\Scripts\python.exe -c "import FinanceDataReader; print(FinanceDataReader.__version__)"

# Reinstall if missing
pip install finance-datareader>=0.9.96
```

---

### Coverage below 75% (CI failure)

```
FAIL Required test coverage of 75.0% not reached. Total coverage: XX%
```

**Fix:** Identify low-coverage modules:
```powershell
.\.venv\Scripts\python.exe -m pytest --cov=stock_rtx4060 --cov-report=term-missing -q 2>&1 | grep "%"
```

Current low-coverage modules (as of 2026-05-07):

| Module | Coverage | Priority |
|--------|----------|----------|
| `ensemble_model.py` | 49% | High — ML train/predict paths |
| `kevpe_adapter.py` | 43% | Medium — external adapter |
| `main.py` | 51% | Medium — CLI dispatch |
| `alert_engine.py` | 73% | Low risk |

---

### `self-test: FAIL` after code changes

**Triage steps:**
```powershell
# 1. Check compilation
.\.venv\Scripts\python.exe -m compileall src/

# 2. Run tests with verbose output
.\.venv\Scripts\python.exe -m pytest -v --tb=short

# 3. Run smoke manually
.\run.ps1 recommend --data-provider synthetic --universe SYNTH-A --track S --top 1 --output-dir reports/debug_smoke
```

---

### XGBoost GPU not used (falls back to CPU)

```
[xgb] device: cpu (fallback)
```

**Verify CUDA:**
```powershell
nvidia-smi
.\.venv\Scripts\python.exe -c "import xgboost as xgb; print(xgb.__version__)"
```

XGBoost ≥ 3.1.0 is required for CUDA support. Reinstall if needed:
```powershell
pip install "xgboost>=3.1.0"
```

---

## Monitoring

### Audit Log

All provider selections (yfinance, pykrx, FDR, cache hit/miss) are recorded in `audit_log.py` as JSONL:

```powershell
# View recent audit entries (if audit log file exists)
type reports\audit_log.jsonl | python -c "import sys,json; [print(json.dumps(json.loads(l), indent=2)) for l in sys.stdin][-5:]" 2>$null
```

### Report Outputs

| Path | Contents |
|------|---------|
| `recommendation_reports/` | Markdown + JSON candidate verdicts |
| `reports/` | Daily Brief, Risk Dashboard, benchmark outputs |
| `reports/audit_log.jsonl` | Provider selection audit trail |

---

## Rollback Procedures

### Rollback a bad `requirements.txt` change

```powershell
# Recreate venv from last known good state
Remove-Item -Recurse .venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
git checkout requirements.txt
pip install -r requirements.txt
pip install -r requirements-dev.txt
python main.py self-test
```

### Rollback a code change

```powershell
git log --oneline -10          # identify last good commit
git diff HEAD~1 HEAD           # review what changed
git revert HEAD                # safe revert (creates new commit)
python main.py self-test       # verify
.\.venv\Scripts\python.exe -m pytest -q  # verify tests
```

### Rollback provider config

```powershell
copy config\data_providers.example.json config\data_providers.json
```

---

## Approval Gates

The following actions require **explicit manual approval** before execution:

| Action | Gate |
|--------|------|
| Add/remove dependencies | Approval required |
| Edit CI workflow (`.github/workflows/`) | Approval required |
| Delete files | Approval required |
| Write outside the repo directory | Approval required |
| Handle secrets or credentials | Hard block |
| Broker/account integrations | Hard block — permanent boundary |
| Live buy/sell orders | Hard block — permanent boundary |
| Margin/options execution | Hard block — permanent boundary |

---

## Security Boundaries (Permanent)

These boundaries cannot be removed by configuration or code change:

- `screening_output_only=True` must remain in all recommendation result objects
- No order routing — `broker_bridge.py` is a stub adapter only
- No credentials, `.env*`, broker keys, or account IDs in any committed file
- Recommendation reports are screening evidence for manual review, not investment advice
