# stock_rtx4060_unified

`stock_rtx4060_unified` is a consolidated, local, report-only stock investment analysis CLI.

It keeps one executable package under `src/stock_rtx4060` and removes duplicate bundle, patch, cache, and generated-output copies from the runtime path.

## Verified Scope

| Area | Current implementation |
|---|---|
| CLI | `main.py` delegates to `src/stock_rtx4060/main.py`. |
| Runner | `run.ps1` resolves `.venv`, Python 3.12, Python 3.11, then `python`. |
| Features | `feature_engine.py` builds lagged Algorithm v2 OHLCV indicators and targets. |
| Model | `ensemble_model.py` supports leak-safe walk-forward CV, OOF probabilities, logistic fallback, XGBoost CPU/CUDA request, and optional LSTM. |
| Backtest | `backtester.py` supports fixed risk, fractional Kelly, costs, slippage, stops, and monthly stop. |
| Recommendation | `recommendation_engine.py` writes `screening_output_only` `recommendations_algo_v2_*.md/json`. |
| Reports | Markdown, JSON, and CSV files are written locally. |

## Run

```powershell
python main.py --help
.\run.ps1 self-test
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations
```

## Test

```powershell
python -m compileall .
pytest
```

If the default `python` lacks pytest, use the validated Python 3.12 interpreter on this machine:

```powershell
C:\Users\jichu\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q
```

## Safety Boundary

This project does not place broker orders. Outputs are screening reports only and require manual review.
