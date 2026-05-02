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

Observed result after OHLCV cache coverage: 15 tests passed.

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

No GPU benchmark is required to run the unified folder's self-test.
