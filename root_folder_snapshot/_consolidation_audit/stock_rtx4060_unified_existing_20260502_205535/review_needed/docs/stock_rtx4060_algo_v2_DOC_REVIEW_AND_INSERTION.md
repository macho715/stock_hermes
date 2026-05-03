# Document Review and Recommendation Feature Insertion

## Review Result

The current document set defines `stock_rtx4060` as a local, report-only Investment Operation OS. The safety boundary is consistent across README, Spec, SYSTEM_ARCHITECTURE, and AGENTS:

- No broker order execution.
- No auto buy/sell.
- Every output must pass Risk Gate.
- All outputs must remain auditable and screening/report-only.

The new user requirement asks the program to recommend stocks directly. This creates a conflict with the previous `Non-Goals` wording that prohibited direct buy/sell recommendations. The safe resolution is:

> Insert a direct `candidate recommendation` feature, not a direct broker-executable buy/sell instruction.

The program now ranks tickers and returns `ELIGIBLE_RECOMMENDATION`, `ACCUMULATE_RECOMMENDATION`, `AMBER_*`, `RED_*`, or `ZERO_*` with multi-confirmation evidence.

## Added Algorithm

### Track-S Short-term Recommendation

Target use: 1-month tactical candidate screening with +10.00% TP2 and -4.00% stop.

Score factors:

| Factor | Weight |
|---|---:|
| Direction model edge | 20.00 |
| Trend / regime | 20.00 |
| Liquidity / volume | 15.00 |
| Breakout proximity | 15.00 |
| Backtest sanity | 15.00 |
| Risk plan | 10.00 |

Green condition:

```text
score >= 75.00
DATA_ROWS pass
LIQUIDITY pass or not failed
MODEL_EDGE pass
BACKTEST_SANITY pass/acceptable
RISK_PLAN pass
manual approval still required
```

### Track-L Long-term Recommendation

Target use: 3-year accumulation candidate screening with +20.00% objective.

Score factors:

| Factor | Weight |
|---|---:|
| Quality proxy | 20.00 |
| Earnings proxy | 15.00 |
| Balance/risk proxy | 10.00 |
| Valuation/overheat proxy | 15.00 |
| Structural theme neutral placeholder | 10.00 |
| Trend | 15.00 |
| Direction model edge | 10.00 |
| Risk review | 10.00 |

Green condition:

```text
score >= 80.00
DATA_ROWS pass
RISK_PLAN pass
multi-confirmation >= 4/6
manual approval still required
```

## Multi-confirmation Checks

| Check | Purpose | Fail Behavior |
|---|---|---|
| DATA_ROWS | Minimum history length | RED_DATA_INSUFFICIENT |
| LIQUIDITY | Avg dollar volume | AMBER or score penalty |
| MODEL_EDGE | Direction probability + CV accuracy/AUC | AMBER or score penalty |
| BACKTEST_SANITY | Sharpe/MDD sanity | AMBER or score penalty |
| RISK_PLAN | Entry/stop/TP/RR | ZERO_RISK_PLAN_FAILED |
| TRACK_SCORE | Track-specific score threshold | Green/Amber/Red |

## New CLI Contract

```powershell
python main.py --recommend --track BOTH --universe AAPL,MSFT,NVDA,AMD,AVGO,GOOGL,AMZN,META,TSLA,QQQ,SPY --period 3y --top 10
```

Synthetic demo:

```powershell
python main.py --recommend --synthetic --universe SYNTH-A,SYNTH-B,SYNTH-C --top 5
```

## New Reports

- `recommendation_reports/recommendations_*.md`
- `recommendation_reports/recommendations_*.json`

## Safety Boundary

`ELIGIBLE_RECOMMENDATION` and `ACCUMULATE_RECOMMENDATION` are screening outputs, not personalized investment advice and not broker order instructions.

## Validation

- `python -m pytest -q main.py`: 5 passed.
- `python main.py --recommend --synthetic --universe SYNTH-A,SYNTH-B,SYNTH-C --top 3`: generated Markdown/JSON recommendation reports.
