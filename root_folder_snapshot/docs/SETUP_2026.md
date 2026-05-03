# SETUP_2026 — Windows RTX 4060 validation path

## 1. CPU-safe install

```powershell
winget install Python.Python.3.11
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py self-test
```

## 2. GPU gate

```powershell
nvidia-smi
python main.py env --xgboost --output reports/runtime_status.json
python main.py benchmark --rows 3000 --repeats 3 --include-gpu
```

Expected interpretation:

- `GREEN`: `nvidia-smi` and XGBoost CUDA smoke test pass.
- `AMBER`: CPU/fallback path works, but GPU is absent, unvalidated, or skipped.
- `RED`: reserved for core runtime failure.

## 3. TensorFlow note

Modern TensorFlow does not treat native Windows GPU as the primary NVIDIA CUDA path after TensorFlow 2.10. Use WSL2 for TensorFlow GPU validation:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-gpu-wsl.txt
python main.py env --tensorflow --xgboost
```

## 4. Benchmark commands

```powershell
python main.py benchmark --rows 1500 --repeats 3 --output-dir reports
python main.py benchmark --rows 5000 --repeats 3 --include-gpu --output-dir reports
python main.py benchmark --rows 1500 --repeats 1 --include-gpu --include-lstm --output-dir reports
```

## 5. Recommendation command

```powershell
python main.py recommend --track BOTH --universe "AAPL,MSFT,NVDA,QQQ,SPY" --period 3y --top 5 --output-dir reports/recommendations
python main.py recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --output-dir reports/recommendations
```

The recommendation output is `screening_output_only`. It is not a broker order or personalized investment advice.

## 6. CSV format

CSV must include columns: `Open`, `High`, `Low`, `Close`, `Volume`. Date index is optional.

```powershell
python main.py report --ticker MYDATA --csv .\data\my_ohlcv.csv --capital 100000 --output-dir reports
```
