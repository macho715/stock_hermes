# stock_rtx4060 Patch Report — 2026 Web Benchmark Edition

## Scope completed

- Rechecked uploaded `plan_rev.md`, `uiux.md`, and `주식.zip` script structure.
- Rebuilt the uploaded scripts into a runnable Python package plus compatibility entrypoint.
- Patched GPU assumptions for 2026 documentation: native Windows TensorFlow GPU is not assumed; WSL2/Linux is documented for modern TensorFlow CUDA.
- Added optional XGBoost CUDA path with CPU fallback.
- Added reproducible offline data fixture, CSV-first data path, optional yfinance data path, report generation, journal CSV, and benchmark harness.
- Added 2026 source/cross-check documents under `docs/`.

## Validation performed in this container

```text
python -S -m py_compile main.py stock_rtx4060/*.py *.py tests/test_smoke.py  -> PASS
python -S main.py --test                                                    -> PASS
python -S main.py --offline --no-model                                      -> PASS
python -S main.py --benchmark --benchmark-rows 300                          -> PASS in prior smoke run
```

## Container benchmark note

This container does not expose an NVIDIA RTX 4060 GPU. The included benchmark is a CPU/offline smoke benchmark only. Run the benchmark commands in `SETUP_2026.md` on the target Windows/WSL2 RTX 4060 environment for true GPU timing.

## Demo benchmark snapshot

```json
{
  "rows": 300,
  "feature_engine_seconds": 0.3815,
  "backtester_seconds": 0.0053,
  "backtest_total_return_pct": -0.94,
  "backtest_sharpe_ratio": -1.166,
  "backtest_max_drawdown_pct": 1.79,
  "n_trades": 9
}
```

## Important limitation

This package is for decision support, research, and backtesting. It does not place broker orders, does not provide guaranteed returns, and does not replace personal financial advice.
