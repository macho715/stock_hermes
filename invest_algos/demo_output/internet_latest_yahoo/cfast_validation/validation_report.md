# C Fast Validation Report

No broker execution. No live trading. Dry-run validation only.

## Verdicts

- A: `HOLD_DIAGNOSTIC_ONLY`
- B: `REJECT_RETRAIN`
- C fast: `VALIDATION_FAILED_REVIEW_REQUIRED`
- target_return_metric: `annualized_net_return`
- target_return_min: `10.00%`
- warnings: `target_return_shortfall_x2, cost_fragile`
- execution_mode: `VALIDATION_FAILED_NO_TRADING`
- promotion_status: `BLOCKED_BY_TARGET_RETURN_SHORTFALL`
- promotion_blockers: `BLOCKED_BY_VALIDATION_FAILED, BLOCKED_BY_TARGET_RETURN_SHORTFALL, BLOCKED_BY_X5_COST_FRAGILITY`

## Cost Stress

| Label | Cost bps | Sharpe | Ann Return | Target Return Min | Target Return Pass | MDD | Optimizer Success | Fallback Rate |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| base | 5.00 | 1.41 | 11.20% | 10.00% | True | -8.19% | 100.00% | 0.00% |
| x2 | 10.00 | 1.62 | 8.78% | 10.00% | False | -5.65% | 100.00% | 0.00% |
| x5 | 25.00 | 0.69 | 1.32% | info | info | -2.71% | 100.00% | 0.00% |

## Data

- rows: 900
- first_date: 2022-10-26
- last_date: 2026-05-29
- columns: SPY, QQQ, IWM, TLT, IEF, GLD, DBC, UUP
