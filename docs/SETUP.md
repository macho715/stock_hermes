# SETUP

## Recommended Runtime

Use the wrapper from the unified folder:

```powershell
cd C:\Users\jichu\Downloads\주식\stock_rtx4060_unified
.\run.ps1 self-test
```

Current observed result: `self-test: PASS`, backend `xgb-cpu`, final capital `102190.84`.

## Install

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
python main.py self-test
```

The project runtime is `.venv\Scripts\python.exe` on Python 3.12. The default global `python` on this machine was Python 3.14.4 during earlier validation; treat that path as AMBER unless it is explicitly prepared.

Run tests through the project `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Observed result after Phase A provider validation coverage: 26 tests passed.

Observed targeted Phase B result: 7 tests passed for Backtest Honesty unit tests, dashboard bridge compatibility, and synthetic recommendation JSON evidence.

Observed full Phase B regression result: 30 tests passed.

## Optional OpenBB Provider

OpenBB is optional in Phase 1. The offline synthetic and current yfinance paths must work without it.

Install only when validating `--data-provider openbb`:

```powershell
pip install -r requirements-openbb.txt
```

The approved first OpenBB endpoint is:

```python
obb.equity.price.historical(symbol="AAPL", provider="yfinance")
```

Provider defaults can be copied from `config/data_providers.example.json`.
CLI flags override the config:

```powershell
.\run.ps1 recommend --data-provider synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations_phase1_smoke
.\run.ps1 recommend --data-provider openbb --provider-config config/data_providers.example.json --universe "AAPL" --top 1 --output-dir reports/recommendations_openbb_cache_smoke
```

Each `recommend` and `ops-v1` run writes `audit_log.jsonl` under the recommendation output directory.
`RecommendationEngine` caches OHLCV data for the same ticker during one CLI run, so a single-ticker `track=BOTH` OpenBB smoke writes one provider event.

## Phase A Provider Validation Smoke

Provider loads run point-in-time OHLCV checks through `src/stock_rtx4060/provider_validation.py`.
The validation metadata is written to `audit_log.jsonl`, recommendation JSON `provider_summary`, and dashboard snapshot `provider_summary`.

```powershell
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/phase_a_provider_v2_smoke
.\run.ps1 dashboard-export --recommendation-json reports/phase_a_provider_v2_smoke/recommendations_algo_v2_YYYYMMDD_HHMMSS.json --output reports/phase_a_provider_v2_smoke/dashboard_snapshot.json --public-dir ..\stock-pred-v5\public
```

The provider validation gate is evidence-only. It does not place orders and does not approve trades.

## Phase B Backtest Honesty Smoke

Backtest honesty checks run after model/backtest metrics are produced.
They are evidence-only and do not approve trades.

Targeted verification:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_backtest_honesty.py tests\test_dashboard_bridge.py::test_build_dashboard_snapshot_preserves_report_only_contract tests\test_dashboard_bridge.py::test_dashboard_snapshot_accepts_older_payload_without_provider_summary tests\test_core.py::test_recommendation_engine_synthetic_run -q
```

Synthetic smoke output should include:

- candidate-level `backtest_honesty`
- top-level `backtest_honesty_summary`
- `dashboard_snapshot.v1.backtest_honesty_summary`
- `audit_log.jsonl` event type `backtest_honesty_summary`

Observed Phase B smoke result: `reports\phase_b_backtest_honesty_smoke\dashboard_snapshot.json` contains `backtest_honesty_summary.status=AMBER`, candidate `backtest_honesty.status=AMBER`, and `screening_output_only=True`.

## Common Commands

```powershell
python main.py --help
.\run.ps1 self-test
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations
.\run.ps1 ops-v1 --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/ops_v1
.\run.ps1 recommend --data-provider synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations_phase1_smoke
.\run.ps1 recommend --data-provider openbb --provider-config config/data_providers.example.json --universe "AAPL" --top 1 --output-dir reports/recommendations_openbb_cache_smoke
.\run.ps1 ops-v1 --period 3y --top 5 --full --prefer-gpu --model-kind xgb --cv-gap 5 --output-dir reports/ops_v1
```

## Dashboard Report Bridge

Generate a recommendation report first:

```powershell
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/dashboard_bridge_smoke
```

Then convert the generated recommendation JSON into a dashboard snapshot:

```powershell
.\run.ps1 dashboard-export --recommendation-json reports/dashboard_bridge_smoke/recommendations_algo_v2_YYYYMMDD_HHMMSS.json --output reports/dashboard_bridge_smoke/dashboard_snapshot.json
```

Open `C:\Users\jichu\Downloads\주식\stock_pred_v5.jsx` in the dashboard host, click `BACKEND`, and choose `dashboard_snapshot.json`.

The bridge is file-based. It does not start a local API server, MCP server, broker connection, or background service.

The repo-owned dashboard copy is:

```text
dashboard/stock_pred_v5.jsx
```

Run browser smoke verification:

```powershell
node dashboard\verify_bridge_smoke.mjs
```

Observed result: PASS. The report is written to `reports/dashboard_browser_verification/dashboard_browser_verification.md`.

## Ops v1 Output

`ops-v1` creates:

- recommendation Markdown/JSON
- recommendation `audit_log.jsonl`
- Ops v1 daily brief
- `approval_journal_template.csv`
- `zero_log.md` and `zero_log.csv`
- Ops v1 summary JSON

The workflow remains `screening_output_only` and stops before broker/account actions.

## GPU Note

Use `requirements-gpu-wsl.txt` only inside WSL2/Linux when TensorFlow GPU validation is needed.

TensorFlow has two separate validation lanes:

```powershell
.\run.ps1 tensorflow-check
.\run.ps1 tensorflow-gpu-wsl-check
```

- `tensorflow-check` validates the native Windows `.venv-tf312` TensorFlow CPU/LSTM smoke.
- `tensorflow-gpu-wsl-check` validates the WSL Ubuntu TensorFlow GPU smoke through `/root/.venvs/stock-rtx4060-tf-gpu`.
- aliases: `.\run.ps1 tf-gpu-wsl`, `.\run.ps1 tf-gpu-smoke`.
- the WSL wrapper sets `LD_LIBRARY_PATH` from the installed NVIDIA pip libraries before TensorFlow starts.
- current verified WSL GPU result: TensorFlow `2.21.0`, RTX 4060 GPU detected as `/physical_device:GPU:0`, GPU matmul PASS, LSTM smoke PASS.

No GPU benchmark is required to run the unified folder's self-test.
