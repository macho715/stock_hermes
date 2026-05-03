# SETUP

## Install

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For tests in a clean environment:

```powershell
pip install -r requirements-dev.txt
```

## Validate

```powershell
python --version
python -m compileall .
python main.py --help
pytest
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

## Common Commands

```powershell
.\run.ps1 self-test
.\run.ps1 env --xgboost --output reports/runtime_status.json
.\run.ps1 benchmark --rows 800 --repeats 1 --output-dir reports/benchmark_smoke
.\run.ps1 recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations
```

## GPU Note

`requirements-gpu-wsl.txt` is for WSL2/Linux TensorFlow GPU validation. Do not install it by default on native Windows.
