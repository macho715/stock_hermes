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
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
python main.py self-test
```

The default `python` on this machine was Python 3.14.4 during validation. It compiled the package and printed CLI help, but it did not have pandas or pytest installed. That path is recorded as AMBER, not PASS.

The Python 3.12 path used for tests was:

```powershell
C:\Users\jichu\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q
```

Observed result: 5 tests passed.

## Common Commands

```powershell
python main.py --help
python main.py self-test
python main.py recommend --synthetic --universe "SYNTH-A,SYNTH-B" --top 2 --model-kind logistic --cv-gap 5 --output-dir reports/recommendations
.\run.ps1 self-test
```

## GPU Note

Use `requirements-gpu-wsl.txt` only inside WSL2/Linux when TensorFlow GPU validation is needed.

No GPU benchmark is required to run the unified folder's self-test.
