# SPEC

## Purpose

`stock_rtx4060_unified` is a consolidated report-only stock screening and backtesting CLI.

## Functional Contract

| Requirement | Contract |
|---|---|
| CLI | Must support `env`, `benchmark`, `report`, `predict`, `recommend`, `demo`, `journal`, and `self-test`. |
| Feature pipeline | Must build lagged OHLCV features and target columns without using future target values as features. |
| Model pipeline | Must report leak-safe walk-forward CV with explicit gap and OOF coverage when available. |
| Recommendation | Must label outputs `screening_output_only` and write local Markdown/JSON reports. |
| Backtest | Must remain dry-run and must not trigger live orders. |
| GPU | Must be validated through explicit runtime checks before performance claims. |

## Non-Goals

- Broker order execution.
- Personalized investment advice.
- Browser dashboard or HTTP API.
- Secret storage.

## Open Items

- 가정: real portfolio capital, broker, market scope, and data vendor are not defined in source files.
