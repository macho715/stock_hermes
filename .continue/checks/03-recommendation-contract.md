---
name: Recommendation Contract
description: Validate that recommendation logic preserves the Algorithm v2 screening contract.
---

Review this change for Track-S and Track-L recommendation behavior.

Fail this check if any change does one or more of the following:

- Removes or bypasses the required gates: `DATA_ROWS`, `LIQUIDITY`, `MARKET_REGIME`, `MODEL_EDGE`, `OOF_COVERAGE`, `BACKTEST_SANITY`, `RISK_PLAN`, `TRACK_SCORE`, or `AUTOMATION_BOUNDARY`.
- Allows a Green Track-S candidate below score 75.00 without an explicit documented rule change and tests.
- Allows a Green Track-L candidate below score 80.00 without an explicit documented rule change and tests.
- Allows stop >= entry, non-positive risk budget, or invalid Risk/Reward to pass.
- Changes `AMBER_REVIEW_ONLY`, `AMBER_WATCHLIST`, `RED_*`, or `ZERO_*` semantics without documentation and tests.
- Allows missing or insufficient OHLCV data to return Green.
- Changes ranking order without documenting verdict priority, score, expected value, ticker, and track behavior.

Pass only if:

- Track-S remains tactical short-term screening.
- Track-L remains long-term accumulation screening.
- Green requires multi-factor evidence and manual review.

When failing, list the broken contract and the required test to add or update.
