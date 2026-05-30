# C Fast Validation Report

No broker execution. No live trading. Dry-run validation only.

## Verdicts

- A: `HOLD_DIAGNOSTIC_ONLY`
- B: `REJECT_RETRAIN`
- C fast: `CONDITIONAL_PASS_PAPER_TRADING_CANDIDATE`
- warnings: `cost_fragile`
- execution_mode: `PAPER_TRADING_DRY_RUN_ONLY`
- promotion_status: `BLOCKED_BY_X5_COST_FRAGILITY`
- promotion_blockers: `BLOCKED_BY_X5_COST_FRAGILITY`

## Cost Stress

| Label | Cost bps | Sharpe | Ann Return | MDD | Optimizer Success | Fallback Rate |
|---|---:|---:|---:|---:|---:|---:|
| base | 5.00 | 1.41 | 11.20% | -8.19% | 100.00% | 0.00% |
| x2 | 10.00 | 1.62 | 8.78% | -5.65% | 100.00% | 0.00% |
| x5 | 25.00 | 0.69 | 1.32% | -2.71% | 100.00% | 0.00% |

## Data

- rows: 900
- first_date: 2022-10-26
- last_date: 2026-05-29
- columns: SPY, QQQ, IWM, TLT, IEF, GLD, DBC, UUP
