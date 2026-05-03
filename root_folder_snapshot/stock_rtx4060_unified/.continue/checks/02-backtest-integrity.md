---
name: Backtest Integrity
description: Enforce leak-safe time-series validation and dry-run backtest integrity.
---

Review this change for backtest and model-validation integrity.

Fail this check if any change does one or more of the following:

- Uses future price, future return, target label, or post-decision data in feature generation.
- Replaces leak-safe `TimeSeriesSplit(gap=...)` or equivalent purged walk-forward validation with random split for market time-series data.
- Fits scalers, feature selectors, hyperparameters, or models on validation/test data.
- Replaces out-of-fold probabilities with final-model in-sample probabilities for backtesting.
- Uses same-day close price for both signal generation and execution without an explicit lag or delay.
- Removes transaction cost, slippage, stop-loss, take-profit, monthly stop, or risk-budget handling from backtest behavior without a replacement.
- Reports model probability alone as sufficient for a Green recommendation.

Pass only if:

- Features are generated only from data available at the decision timestamp.
- OOF probabilities remain available for dry-run backtesting when applicable.
- Risk/Reward, stop, target, cost, slippage, and drawdown logic remain auditable.

When failing, suggest the minimal patch that restores leak-safe validation.
