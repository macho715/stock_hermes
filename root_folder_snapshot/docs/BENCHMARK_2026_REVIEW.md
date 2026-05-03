# BENCHMARK_2026_REVIEW

## Sources checked

- TensorFlow pip install documentation: Windows native GPU support ended at TensorFlow 2.10; WSL2 is the supported NVIDIA GPU path for newer TensorFlow.
- XGBoost GPU support documentation: CUDA 12.0 and Compute Capability 5.0+ are required; Python GPU acceleration uses `device="cuda"`.
- NVIDIA CUDA Windows installation guide: pip-installable CUDA runtime packages exist for CUDA 12.
- RAPIDS cuDF 26.04 docs: `cudf.pandas` can accelerate pandas code on GPU with fallback, but this project keeps pandas as the portable baseline and records cuDF as optional future acceleration.
- yfinance GitHub docs: data is intended for research/personal use and is not affiliated with Yahoo; script supports CSV fallback.
- backtesting.py and vectorbt GitHub docs: both emphasize backtesting as analysis/education, not guaranteed trading results.

## Local benchmark executed in this sandbox

```bash
python3 main.py self-test
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
python3 main.py benchmark --rows 800 --repeats 2 --output-dir reports
python3 main.py demo --workspace demo_workspace
```

Observed sandbox benchmark:

| Step | Backend | Rows | Best seconds |
|---|---:|---:|---:|
| feature_engine.build_all | pandas/numpy | 591 | 1.190640 |
| walk_forward_train | numpy-logistic | 591 | 0.204867 |
| backtester.run | python/pandas | 591 | 0.020520 |

GPU benchmark was not executed in this sandbox because no RTX 4060/NVIDIA CUDA runtime is available here. The patched script records GPU fallback behavior instead of silently claiming GPU speedup.

## Benchmark item meanings

| Step | Meaning | Comparison rule |
|---|---|---|
| `feature_engine.build_all` | Builds model features from synthetic or input price data. | Not a model training speed comparison. |
| `walk_forward_train` | CPU baseline using deterministic NumPy logistic scoring. | Use as a lightweight baseline only. |
| `walk_forward_train_xgboost_cpu` | XGBoost training with the same model settings as the GPU path and `device="cpu"`. | Compare this with `walk_forward_train_gpu_requested` for CPU XGBoost vs GPU XGBoost. |
| `walk_forward_train_gpu_requested` | XGBoost training requested with CUDA. | Treat as GPU only when backend reports `xgboost-cuda`; otherwise it is a fallback result. |
| `backtester.run` | Runs the dry-run report backtest from generated signals. | Measures report/backtest plumbing, not model training. |

Current RTX 4060 session evidence from `actual_execution_workspace/benchmarks_xgb_cpu_gpu_10000` showed `walk_forward_train_xgboost_cpu` at 2.519635 seconds with backend `xgboost-cpu`, and `walk_forward_train_gpu_requested` at 1.194197 seconds with backend `xgboost-cuda`. This means the same-setting XGBoost GPU path was faster in that run, while `walk_forward_train` remains a separate NumPy baseline.

## Implementation decisions

| Area | Decision | Reason |
|---|---|---|
| TensorFlow GPU | WSL2-only validation gate | Avoids false-positive Windows native GPU claims. |
| XGBoost GPU | `device="cuda"` only when requested | Aligns with current XGBoost API and keeps CPU path deterministic. |
| cuDF | Not enabled by default | Windows/WSL setup and dependency size make it a future optional acceleration path. |
| yfinance | Optional; CSV fallback supported | Avoids data-source fragility and usage-right ambiguity. |
| Backtesting | Internal simple engine + reports | Keeps risk rules explicit; avoids overfitting/black-box strategy assumptions. |
