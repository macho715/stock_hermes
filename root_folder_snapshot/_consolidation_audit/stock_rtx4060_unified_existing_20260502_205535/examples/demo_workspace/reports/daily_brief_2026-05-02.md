# Daily Brief — 2026-05-02

## Scope

- Ticker: `DEMO`
- Purpose: decision support only; no automated order execution.
- Model signal: **BUY**
- Direction probability: 0.583
- XGB backend: `disabled-rule-signal`
- LSTM backend: `disabled`

## Track-S Candidate

| ticker   |   score | gate   |   risk_reward |   position_value |   quantity |   entry |    stop |   target_1 |   target_2 | reasons                                                                                                                              |
|:---------|--------:|:-------|--------------:|-----------------:|-----------:|--------:|--------:|-----------:|-----------:|:-------------------------------------------------------------------------------------------------------------------------------------|
| DEMO     |      72 | AMBER  |           2.5 |          2442.14 |         22 | 111.006 | 106.566 |    116.556 |    122.107 | ['Market regime positive', '20D relative strength positive', 'Volume expansion moderate', 'Catalyst confirmed', 'Risk/reward >=2.0'] |


## Backtest Snapshot

|   total_return_pct |   sharpe_ratio |   max_drawdown_pct |   win_rate |   n_trades |   final_capital |
|-------------------:|---------------:|-------------------:|-----------:|-----------:|----------------:|
|              -0.19 |         -0.131 |               1.16 |      47.06 |         17 |         19961.2 |


## Notes

- `GREEN` means rule-qualified candidate for manual review; it is not a buy order.
- `ZERO` means execution is blocked by risk policy.
