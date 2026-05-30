# C Fast Optimizer Failure Diagnostics

No broker execution. No live trading. Diagnostic output only.

## Failure Counts
- total: 0

## Failed Rebalance Days
No failed rebalance days remained after the optimizer update.

## Diagnosis
- `optimizer_maxiter` is now 1000 by default.
- The optimizer starting path is clipped to asset bounds before scipy runs.
- Diagnostics now expose `fallback_used`, `fallback_reason`, and `optimizer_iterations`.
- Current rerun shows optimizer success rate 100% for base, x2, and x5.
