# C Fast Validation Report

No broker execution. No live trading. Dry-run validation only.

## Verdicts

- A: `HOLD_DIAGNOSTIC_ONLY`
- B: `REJECT_RETRAIN`
- C fast: `CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE`
- target_return_metric: `annualized_net_return`
- target_return_min: `10.00%`
- warnings: `dbc_weight_floor_breach`
- execution_mode: `PAPER_TRADING_DRY_RUN_ONLY`
- promotion_status: `READY_FOR_PAPER_TRADING_REVIEW`
- promotion_blockers: `none`

## Forward-Month Gate

- forward_pass: `True`
- forward_return: `2.53%`
- forward_mdd: `-0.47%`

## Cost Stress

| Label | Cost bps | Sharpe | Ann Return | Target Return Min | Target Return Pass | MDD | Optimizer Success | Fallback Rate |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| base | 5.00 | 1.52 | 11.65% | 10.00% | True | -7.08% | 100.00% | 0.00% |
| x2 | 10.00 | 1.52 | 13.06% | 10.00% | True | -9.38% | 100.00% | 0.00% |
| x5 | 25.00 | 1.44 | 7.33% | info | info | -5.72% | 100.00% | 0.00% |

## Data

- rows: 900
- first_date: 2022-10-26
- last_date: 2026-05-29
- columns: SPY, QQQ, IWM, TLT, IEF, GLD, DBC, UUP
