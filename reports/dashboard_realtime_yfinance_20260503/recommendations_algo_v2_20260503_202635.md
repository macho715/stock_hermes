# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-03T16:26:35+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, QQQ, SPY
Track: BOTH | Period: 6mo | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\dashboard_realtime_yfinance_20260503\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | AAPL | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | AAPL: 데이터 부족 rows=124, required=283 |
| 2 | AAPL | S | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | AAPL: 데이터 부족 rows=124, required=260 |
| 3 | MSFT | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | MSFT: 데이터 부족 rows=124, required=283 |
| 4 | MSFT | S | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | MSFT: 데이터 부족 rows=124, required=260 |
| 5 | NVDA | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | NVDA: 데이터 부족 rows=124, required=283 |

## Validation details

### AAPL / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — AAPL: 데이터 부족 rows=124, required=283

### AAPL / Track-S / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — AAPL: 데이터 부족 rows=124, required=260

### MSFT / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — MSFT: 데이터 부족 rows=124, required=283

### MSFT / Track-S / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — MSFT: 데이터 부족 rows=124, required=260

### NVDA / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — NVDA: 데이터 부족 rows=124, required=283
