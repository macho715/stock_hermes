# Benchmark Report — stock_rtx4060 patched

Generated: `2026-05-02T09:38:42`

## Hardware Probe

```json
{
  "cpu_model": "Intel Core i5-13500HX target / detected CPU via OS",
  "os_name": "Linux 4.4.0",
  "python_version": "3.13.5",
  "is_windows": false,
  "is_wsl": false,
  "workers": 16,
  "nvidia_smi": {
    "available": false,
    "name": "N/A",
    "driver_version": "N/A",
    "cuda_runtime": "N/A",
    "memory_total_mib": null,
    "raw": ""
  }
}
```

## Timings

| name             |   seconds |   rows | notes                                |
|:-----------------|----------:|-------:|:-------------------------------------|
| make_dummy_ohlcv |    0.0072 |    300 | offline deterministic data           |
| feature_engine   |    0.3815 |    300 | vectorized pandas/numpy              |
| backtester       |    0.0053 |     96 | Track-S stop/TP/time-stop simulation |

## Backtest Summary

|   total_return_pct |   sharpe_ratio |   max_drawdown_pct |   win_rate |   n_trades |   final_capital |
|-------------------:|---------------:|-------------------:|-----------:|-----------:|----------------:|
|              -0.94 |         -1.166 |               1.79 |      44.44 |          9 |         99043.1 |

## 2026 Technical Baseline Applied

| Area | Patch decision |
|---|---|
| TensorFlow GPU | Native Windows CUDA is not assumed. WSL2/Linux path is preferred; native Windows falls back to CPU. |
| XGBoost GPU | Uses `device='cuda'` + `tree_method='hist'` only when GPU is requested/detected, with CPU fallback. |
| pandas I/O | CSV loader attempts `engine='pyarrow'` / `dtype_backend='pyarrow'`, then falls back to standard pandas. |
| Backtesting | Uses internal event simulator to avoid AGPL coupling while cross-checking vectorized backtest practices. |
| yfinance | Treated as research/education data source; CSV path remains first-class for reproducibility. |

## Re-run on target RTX 4060

```powershell
python -m stock_rtx4060.benchmark --rows 3000 --model --prefer-gpu --out ./benchmark_out
```
