# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-08T21:00:49+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: 005930.KS, 000660.KS, 005380.KS, 005490.KS, 035420.KS, 035720.KS, 051910.KS, 006400.KS, 003670.KS
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports/api_recommend_krx/audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 000660.KS | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | 000660.KS: yfinance provider failed: empty OHLCV frame |
| 2 | 000660.KS | S | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | 000660.KS: yfinance provider failed: empty OHLCV frame |
| 3 | 003670.KS | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | 003670.KS: yfinance provider failed: empty OHLCV frame |
| 4 | 003670.KS | S | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | 003670.KS: yfinance provider failed: empty OHLCV frame |
| 5 | 005380.KS | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | 005380.KS: yfinance provider failed: empty OHLCV frame |

## Validation details

### 000660.KS / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — 000660.KS: yfinance provider failed: empty OHLCV frame

### 000660.KS / Track-S / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — 000660.KS: yfinance provider failed: empty OHLCV frame

### 003670.KS / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — 003670.KS: yfinance provider failed: empty OHLCV frame

### 003670.KS / Track-S / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — 003670.KS: yfinance provider failed: empty OHLCV frame

### 005380.KS / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — 005380.KS: yfinance provider failed: empty OHLCV frame
