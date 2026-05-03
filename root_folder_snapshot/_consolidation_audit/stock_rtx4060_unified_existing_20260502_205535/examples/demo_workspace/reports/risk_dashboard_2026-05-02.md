# Risk Dashboard — 2026-05-02

## Allocation

| Track   | Allocation   |   Value | Max Loss Rule          |
|:--------|:-------------|--------:|:-----------------------|
| Track-S | 20.00%       |   20000 | monthly -5% stop       |
| Track-L | 75.00%       |   75000 | quarterly -12% review  |
| Cash    | 5.00%        |    5000 | not for Track-S rescue |


## Gate Checks

| Check           | Value   |
|:----------------|:--------|
| Track-S gate    | AMBER   |
| Track-S score   | 72.0    |
| Risk/reward     | 2.5     |
| Backtest MDD    | 1.16%   |
| Backtest Sharpe | -0.131  |


## ZERO Rules

- No stop price → ZERO
- Track-S monthly PnL ≤ -5.00% → ZERO
- Track-S open risk > 2.00% → ZERO
- Automatic buy/order placement → ZERO
- Excessive margin/options/0DTE use → ZERO
