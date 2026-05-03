# Benchmark and 2× GitHub Cross-Check

## Official technology basis checked

| Area | Reference used | Patch impact |
|---|---|---|
| TensorFlow GPU on Windows | Official TensorFlow pip install page, 2026 version | TensorFlow/LSTM path is optional; Windows Native GPU is not assumed. |
| XGBoost GPU | Official XGBoost GPU support docs | CUDA backend uses `device="cuda"` plus `tree_method="hist"`; CPU/sklearn fallback is retained. |
| Time-series validation | scikit-learn `TimeSeriesSplit` docs | Walk-forward CV uses time-ordered splits and horizon-sized `gap`. |

## Cross-check table

| Repo | What was checked | Adopted | Deferred |
|---|---|---|---|
| `dmlc/xgboost` | GPU docs and GitHub GPU prediction tests using `XGBRegressor(tree_method="hist", device=device)` | `--prefer-gpu` requests `device="cuda"`; the code falls back to CPU when validation fails. | Multi-GPU/distributed training. |
| `scikit-learn/scikit-learn` | `TimeSeriesSplit` docs and active 2026 documentation issue context | sklearn backend default, `TimeSeriesSplit(gap=horizon)`, reproducible offline benchmark. | Custom purged/embargo CV beyond sklearn API. |

## Local benchmark policy

This environment may not have an NVIDIA GPU. The generated benchmark is CPU/offline unless `--benchmark-model --prefer-gpu` passes on the target RTX 4060 system.

```powershell
python main.py --benchmark --workspace .\workspace --benchmark-rows 900
python main.py --benchmark --benchmark-model --prefer-gpu --workspace .\workspace --benchmark-rows 900
```
