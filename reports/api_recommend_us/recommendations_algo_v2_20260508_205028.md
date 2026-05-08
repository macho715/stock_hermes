# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-08T20:50:28+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, SPY, QQQ
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports/api_recommend_us/audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | AAPL | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | AAPL: yfinance provider failed: empty OHLCV frame |
| 2 | AAPL | S | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | AAPL: yfinance provider failed: empty OHLCV frame |
| 3 | AMZN | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | AMZN: yfinance provider failed: empty OHLCV frame |
| 4 | AMZN | S | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | AMZN: yfinance provider failed: empty OHLCV frame |
| 5 | GOOGL | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | GOOGL: yfinance provider failed: empty OHLCV frame |

## Validation details

### AAPL / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — AAPL: yfinance provider failed: empty OHLCV frame

### AAPL / Track-S / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — AAPL: yfinance provider failed: empty OHLCV frame

### AMZN / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — AMZN: yfinance provider failed: empty OHLCV frame

### AMZN / Track-S / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — AMZN: yfinance provider failed: empty OHLCV frame

### GOOGL / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — GOOGL: yfinance provider failed: empty OHLCV frame
