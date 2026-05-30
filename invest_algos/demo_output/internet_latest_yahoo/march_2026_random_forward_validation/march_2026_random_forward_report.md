# March 2026 Random Forward Validation

No broker execution. No live trading. Dry-run validation only.

- random_seed: `202603`
- asof_random_trading_day: `2026-03-04`
- forward_window: `2026-03-05` to `2026-05-29`
- forward_periods: `60`

## Forward Results

| Group | Name | Policy | Cash | Risky | Net Total Return | Net Sharpe | Net MDD |
|---|---|---|---:|---:|---:|---:|---:|
| algorithm | A | HOLD_DIAGNOSTIC_ONLY | 100.00% | 0.00% | 0.00% | 0.00 | 0.00% |
| algorithm | B | REJECT_RETRAIN | 80.00% | 20.00% | 0.09% | 0.13 | -1.79% |
| algorithm | C_fast | CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE | 91.80% | 8.20% | 0.08% | 1.19 | -0.12% |
| benchmark | SPY_100 |  | 0.00% | 100.00% | 10.72% | 3.05 | -6.99% |
| benchmark | EQUAL_8ETF |  | 0.00% | 100.00% | 4.88% | 2.45 | -3.62% |
| benchmark | CASH_100 |  | 100.00% | 0.00% | 0.00% | 0.00 | 0.00% |

## Interpretation

- A: net total return 0.00%, cash 100.00%, risky 0.00%.
- B: net total return 0.09%, cash 80.00%, risky 20.00%.
- C_fast: net total return 0.08%, cash 91.80%, risky 8.20%.
- C fast remains paper-trading dry-run only; live trading and broker execution remain blocked.
