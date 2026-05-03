# TensorFlow Install Plan

Generated: 2026-05-03
Scope: `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified`
Status: Completed with isolated Python 3.12 TensorFlow CPU environment

## Phase 1: Business Review

### 1.1 Problem Definition

Current state: `stock_rtx4060_unified` can run XGBoost CUDA smoke successfully, but TensorFlow is not installed.

Target state: install TensorFlow without breaking the working XGBoost GPU recommendation path, then run a minimal TensorFlow import/smoke check.

Confirmed local evidence:

| Check | Result |
|---|---|
| Default Python | Python 3.14.4 |
| Python launcher | Python 3.14, Python 3.12, uv CPython 3.10 |
| Project `.venv` | Python 3.12.4 |
| TensorFlow in project `.venv` | Not installed |
| `py -3.12 -m pip index versions tensorflow` | TensorFlow 2.21.0 available |
| `py -3.14 -m pip index versions tensorflow` | No matching distribution |
| Native Windows TensorFlow GPU | Not supported after TensorFlow 2.10 by official docs |

Official documentation evidence:

| Source | Relevant fact |
|---|---|
| TensorFlow pip install docs | Windows Native has no GPU support after TF 2.10; Windows WSL2 is the GPU-supported Windows path |
| TensorFlow pip install docs | Supported Python range includes Python 3.9-3.12 for the published pip install page |
| TensorFlow Windows source docs | Starting TF 2.11, CUDA build is not supported for native Windows; use WSL2 or CPU/DirectML path |

### 1.2 Options

| Option | Description | Effort | Risk | Cost (AED) |
|---|---|---:|---|---:|
| A | Install TensorFlow into existing project `.venv` Python 3.12 | 0.25 day | Medium: may alter the working XGBoost environment | 0 |
| B | Create isolated `.venv-tf312` with Python 3.12 and install TensorFlow CPU there | 0.5 day | Low: preserves current `.venv` and XGBoost path | 0 |
| C | Build WSL2 TensorFlow GPU path for RTX 4060 | 1-2 days | Medium/High: WSL2, CUDA, cuDNN, package alignment required | 0 |

### 1.3 Recommendation

Recommended option: B.

Reason:
- Python 3.12 is already installed and TensorFlow 2.21.0 is available for that interpreter.
- It avoids changing the working XGBoost GPU `.venv`.
- It gives a clean TensorFlow CPU/LSTM smoke lane first; WSL2 GPU can be a later upgrade if LSTM GPU is truly needed.

Rollback strategy:
- Remove `.venv-tf312` only; do not touch `.venv`, `run.ps1`, or existing XGBoost reports.

### 1.4 Approval And Execution Result

- [x] Phase 1 approved: create `.venv-tf312`, install TensorFlow, run import/smoke checks, and record results.

Planned commands after approval:

```powershell
cd C:\Users\jichu\Downloads\주식\stock_rtx4060_unified
py -3.12 -m venv .venv-tf312
.\.venv-tf312\Scripts\python.exe -m pip install --upgrade pip
.\.venv-tf312\Scripts\python.exe -m pip install tensorflow
.\.venv-tf312\Scripts\python.exe -c "import tensorflow as tf; print(tf.__version__); print(tf.config.list_physical_devices())"
```

Acceptance criteria after approval:

| Check | Expected result |
|---|---|
| Environment isolation | `.venv-tf312` exists; existing `.venv` remains untouched |
| TensorFlow import | `import tensorflow as tf` succeeds |
| Version output | TensorFlow version prints |
| Device output | CPU device visible; GPU may be absent on native Windows |
| Existing path preserved | Existing XGBoost recommendation smoke artifacts remain in place |

## Phase 1 Execution Result

Executed: 2026-05-03

| Check | Result |
|---|---|
| `.venv-tf312` creation | PASS: Python 3.12.4 venv created |
| pip upgrade | PASS: pip upgraded from 24.0 to 26.1 inside `.venv-tf312` |
| TensorFlow install | PASS: `tensorflow-2.21.0` installed |
| TensorFlow import | PASS: `TF_VERSION=2.21.0` |
| Device check | PASS/AMBER: CPU device visible; no native Windows GPU device |
| LSTM smoke | PASS: one-epoch minimal LSTM fit and prediction completed |
| Prediction shape | PASS: `PRED_SHAPE=(2, 1)` |
| Existing `.venv` | PASS: existing project `.venv` was not used for TensorFlow install |

Observed device output:

```text
DEVICES=["/physical_device:CPU:0:CPU"]
```

Observed LSTM smoke output:

```text
LSTM_SMOKE=PASS
LOSS=0.676896
PRED_SHAPE=(2, 1)
```

## Wrapper Command

`run.ps1` now exposes a TensorFlow-only verification path that always uses `.venv-tf312` and does not route through `main.py`.

```powershell
cd C:\Users\jichu\Downloads\주식\stock_rtx4060_unified
.\run.ps1 tensorflow-check
```

Aliases:

```powershell
.\run.ps1 tf-check
.\run.ps1 tf-smoke
```

Latest wrapper verification:

| Command | Result |
|---|---|
| `.\run.ps1 tensorflow-check` | PASS: printed `TF_VERSION=2.21.0`, CPU device, `LSTM_SMOKE=PASS`, `PRED_SHAPE=(2, 1)` |
| `.\run.ps1 tf-smoke` | PASS: alias uses the same `.venv-tf312` smoke |
| `.\run.ps1 --help` | PASS: normal `main.py` wrapper path still works |

Important limitation:

- Native Windows TensorFlow GPU remains unavailable for this install path.
- TensorFlow emitted the expected warning that GPU support is not available on native Windows for TensorFlow >= 2.11.
- RTX 4060 GPU acceleration remains available through the already verified XGBoost CUDA path, not through this TensorFlow CPU venv.
- This limitation applies to the Windows `.venv-tf312` lane only. The separate WSL2 lane below is the verified TensorFlow GPU path.

## WSL2 TensorFlow GPU Wrapper

2026-05-03 update: TensorFlow GPU was verified in WSL Ubuntu through a separate WSL-only environment.

Environment:

| Item | Value |
|---|---|
| WSL distro | `Ubuntu` |
| Python | `3.12.3` |
| WSL venv | `/root/.venvs/stock-rtx4060-tf-gpu` |
| TensorFlow | `2.21.0` |
| NVIDIA GPU | RTX 4060 Laptop GPU, driver `581.83`, VRAM `8188 MiB` |

Wrapper commands:

```powershell
cd C:\Users\jichu\Downloads\주식\stock_rtx4060_unified
.\run.ps1 tensorflow-gpu-wsl-check
.\run.ps1 tf-gpu-wsl
.\run.ps1 tf-gpu-smoke
```

The wrapper sets `LD_LIBRARY_PATH` from `/root/.venvs/stock-rtx4060-tf-gpu/lib/python3.12/site-packages/nvidia/**/lib` before TensorFlow starts.

Latest WSL GPU wrapper verification:

| Command | Result |
|---|---|
| `.\run.ps1 tensorflow-gpu-wsl-check` | PASS: `TF_GPUS=["/physical_device:GPU:0"]`, `GPU_MATMUL=PASS`, `LSTM_SMOKE=PASS` |
| `.\run.ps1 tf-gpu-smoke` | PASS: alias uses the same WSL TensorFlow GPU smoke |

Remaining boundary:

- Windows `.venv-tf312` remains CPU-only.
- WSL TensorFlow GPU depends on the WSL venv path and NVIDIA pip library path listed above.
