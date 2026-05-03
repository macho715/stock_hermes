# 2× GitHub Cross-Check

| Repo / docs | Observed interface or policy | Patch response |
|---|---|---|
| dmlc/xgboost / XGBoost docs | GPU acceleration uses `device="cuda"`; CUDA 12.0 and Compute Capability 5.0+ are required. | `hw_profile.xgb_params()` emits `tree_method="hist"`, `device="cuda"` only when GPU is requested; `env` runs smoke test. |
| ranaroussi/yfinance | Research/personal-use data source; not affiliated with Yahoo; `download` is one of the main components. | yfinance is optional. CSV input is the first-class path for reproducible reports. |
| kernc/backtesting.py | Backtesting framework with simple API, fast execution, built-in optimizer, detailed results. | Internal backtester keeps comparable outputs but no auto-optimizer to reduce overfit risk. |
| polakowo/vectorbt | Large-scale backtesting; disclaimer warns not to risk money users cannot afford to lose. | Reports include no-broker-order guardrail and keep decisions as review artifacts. |
