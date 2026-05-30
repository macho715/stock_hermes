# March 2026 All-Days Forward Validation

No broker execution. No live trading. Dry-run validation only.

- source_latest_date: `2026-05-29`
- march_trading_days: `22`

## Average Forward Results

| Group | Name | Dates | Avg Cash | Avg Risky | Avg Total Return | Median Total Return | Min Return | Max Return | Avg Sharpe | Avg MDD | Positive Rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| algorithm | A | 22 | 100.00% | 0.00% | 0.00% | 0.00% | -0.00% | 0.00% | 0.00 | -0.00% | 4.55% |
| algorithm | B | 22 | 91.82% | 8.18% | 0.29% | 0.25% | 0.00% | 0.88% | 0.61 | -0.60% | 77.27% |
| algorithm | C_fast | 22 | 93.35% | 6.65% | 0.04% | 0.08% | -1.08% | 0.74% | 0.81 | -0.38% | 63.64% |
| benchmark | SPY_100 | 22 | 0.00% | 100.00% | 14.23% | 14.21% | 10.51% | 19.70% | 5.08 | -4.68% | 100.00% |
| benchmark | EQUAL_8ETF | 22 | 0.00% | 100.00% | 6.36% | 5.70% | 4.43% | 8.71% | 4.00 | -2.64% | 100.00% |
| benchmark | CASH_100 | 22 | 100.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00 | 0.00% | 0.00% |

## Interpretation

- A: average total return 0.00%, average cash 100.00%, positive-return rate 4.55%.
- B: average total return 0.29%, average cash 91.82%, positive-return rate 77.27%.
- C_fast: average total return 0.04%, average cash 93.35%, positive-return rate 63.64%.
- C fast remains paper-trading dry-run only; live trading and broker execution remain blocked.
