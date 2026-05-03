# SETUP - Windows i5-13500HX + RTX 4060 Laptop

## 1. CPU-safe install

Fastest local run if Python 3.12 already has dependencies:

```powershell
.\run.ps1 self-test
.\run.ps1 demo --workspace .\workspaces\demo_workspace
```

Isolated environment setup:

```powershell
winget install Python.Python.3.11
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py self-test
```

`python main.py --test` is still accepted as a legacy alias, but new docs should use `self-test`.

`requirements.txt` includes the active Algorithm v2 runtime dependencies: `numpy`, `pandas`, `scikit-learn`, `tabulate`, `yfinance`, and `xgboost`.

## 2. Runtime and GPU validation

```powershell
nvidia-smi
.\run.ps1 env --xgboost --output reports/runtime_status.json
.\run.ps1 benchmark --rows 3000 --repeats 3 --include-gpu --output-dir reports
```

Interpretation:

- `GREEN`: `nvidia-smi` and XGBoost CUDA smoke test pass.
- `AMBER`: CPU/fallback path works, but GPU is absent, unvalidated, or skipped.
- `RED`: core runtime failure.

## 3. TensorFlow note

Modern TensorFlow does not treat native Windows GPU as the primary NVIDIA CUDA path after TensorFlow 2.10. Use WSL2/Linux for TensorFlow GPU validation:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-gpu-wsl.txt
python main.py env --tensorflow --xgboost
```

## 4. Common commands

```powershell
.\run.ps1 predict --ticker AAPL --horizon 5 --period 5y
.\run.ps1 predict --ticker 005930.KS --horizon 5 --period 3y
.\run.ps1 predict --ticker NVDA --period 3y --prefer-gpu
.\run.ps1 predict --ticker TSLA --period 3y --prefer-gpu
.\run.ps1 predict --ticker AAPL --lite
.\run.ps1 report --ticker MYDATA --csv .\data\my_ohlcv.csv --capital 100000 --output-dir reports
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind xgb --xgb-device cuda --output-dir reports/recommendations
.\run.ps1 demo --workspace .\workspaces\demo_workspace
```

## 5. CSV format

CSV input must include these columns:

```text
Open, High, Low, Close, Volume
```

Date index is optional. CSV input is preferred for reproducible reports.

## 6. Project layout

```text
workspaces/stock_rtx4060/
├── hw_profile.py
├── feature_engine.py
├── ensemble_model.py
├── backtester.py
├── risk_rules.py
├── recommendation_engine.py
├── reports.py
├── benchmark.py
└── main.py
```

The root `main.py`, `feature_engine.py`, `ensemble_model.py`, `backtester.py`, and `hw_profile.py` files are compatibility wrappers for the package modules.

`recommendation_engine.py` ranks Track-S / Track-L candidates for manual review and writes `screening_output_only` Markdown/JSON reports. It does not submit broker orders.

Algorithm v2 details now live in the active package:

- `feature_engine.py`: lagged OHLCV indicators and target columns.
- `ensemble_model.py`: leak-safe walk-forward CV, OOF probabilities, logistic/XGBoost paths.
- `backtester.py`: fixed risk, fractional Kelly, costs, slippage, stop/take-profit, monthly stop.
- `recommendation_engine.py`: ATR stop/target planning and `recommendations_algo_v2_*.md/json` output.

