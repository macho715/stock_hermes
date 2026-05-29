# FINAL_PLAN_STOCK_PRED_EXTERNAL_CROSSCHECK_005930_20260529

## Verdict

DONE for plan adoption.

The user report is acceptable as a P0 improvement direction. External close, volume, and target-price numbers are not accepted as final investment evidence until locked by KRX, broker API, or an equivalent primary market-data source.

## Final Decisions

| Item | Decision |
| --- | --- |
| PLAN_DOC adoption | YES |
| External close/volume immediate confirmation | NO |
| Target price 530,000-550,000 KRW immediate confirmation | NO |
| HBM4E event | Reflect through Event Shock Gate |
| SELL to BUY auto-conversion | Prohibited |
| SELL to AMBER revalidation | Allowed |
| Priority implementation | Final bar lock + Volume breakout + Event shock + Dashboard conflict gate |
| 30-day recorder | Keep paper-only |
| Auto promotion | Prohibited |
| New capital | Prohibited |
| Broker order | Prohibited |

## Evidence Policy

Reuters reported that Samsung Electronics shipped 12-layer HBM4E samples to customers and that the news contributed to a share-price jump. This supports an event-shock input.

The final close, final volume, and institutional target-price values must remain AMBER candidate evidence until confirmed by KRX, broker API, or source-locked securities-report evidence.

## Implementation Priority

1. Final Bar Lock
2. Source Priority Rule
3. Volume Breakout Gate
4. Event Shock Gate
5. Model Disagreement Gate
6. Backtest Underperformance Gate
7. Dashboard Conflict Badge
8. Forward Recorder AMBER mode

## Required Final State

```json
{
  "readiness_status": "AMBER_DATA_LAG_EVENT_CONFLICT",
  "investment_execution_ready": false,
  "paper_recording_allowed": true,
  "live_review_candidate": false,
  "auto_promote": false,
  "new_capital_allowed": false,
  "broker_order_execution": false,
  "manual_approval_required": true
}
```

## Gate Rules

Final bar lock must block investment execution when cache, intraday, or unconfirmed bars are used after the market close.

Volume breakout must not force BUY. If volume breakout evidence depends on unconfirmed close or volume values, the result stays AMBER until final data is locked.

Event shock must not force BUY. If a SELL signal conflicts with HBM4E, AI semiconductor, target-price-upgrade, or similar verified positive event evidence, the result moves to AMBER revalidation.

Forward recorder must stay paper-only for 30 trading days. It must not auto-promote candidates into live review.
