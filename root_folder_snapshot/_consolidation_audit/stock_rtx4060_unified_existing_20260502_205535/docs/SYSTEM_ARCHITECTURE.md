# SYSTEM_ARCHITECTURE

## Overview

`stock_rtx4060_unified` is a local Python CLI. It has no HTTP API, no web server, and no broker execution integration.

## Component Diagram

```mermaid
flowchart TD
    User[Operator] --> Run[run.ps1]
    User --> Main[main.py]
    Run --> Main
    Main --> CLI[src/stock_rtx4060/main.py]
    CLI --> Feature[feature_engine.py]
    CLI --> Model[ensemble_model.py]
    CLI --> Risk[risk_rules.py]
    CLI --> Backtest[backtester.py]
    CLI --> Recommend[recommendation_engine.py]
    CLI --> Reports[reports.py]
    CLI --> Env[hw_profile.py]
    Feature --> Model
    Model --> Backtest
    Model --> Recommend
    Risk --> Recommend
    Backtest --> Reports
    Recommend --> Out[Markdown/JSON reports]
    Reports --> Out
```

## Data Flow

```mermaid
flowchart LR
    A[CSV, yfinance, or synthetic OHLCV] --> B[normalize_ohlcv]
    B --> C[Algorithm v2 lagged features]
    C --> D[leak-safe CV with gap]
    D --> E[OOF probabilities]
    E --> F[dry-run backtest]
    D --> G[risk-gated recommendation]
    F --> H[Markdown/JSON outputs]
    G --> H
```

## Boundaries

| Boundary | State |
|---|---|
| Broker orders | Not implemented. |
| Web dashboard | Not implemented. |
| Runtime state | Local reports only. |
| Secrets | No secret loader found in selected runtime path. |
