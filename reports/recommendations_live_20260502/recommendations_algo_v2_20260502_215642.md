# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-02T17:56:42+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, AMD, AVGO, GOOGL, AMZN, META, TSLA, JPM, XOM, LLY, UNH, COST, QQQ, SPY, XLK, XLE, GLD
Track: BOTH | Period: 3y | Top-N: 5

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | AAPL | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | yfinance가 설치되지 않았습니다. pip install yfinance 또는 --synthetic 사용 |
| 2 | AAPL | S | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | yfinance가 설치되지 않았습니다. pip install yfinance 또는 --synthetic 사용 |
| 3 | AMD | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | yfinance가 설치되지 않았습니다. pip install yfinance 또는 --synthetic 사용 |
| 4 | AMD | S | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | yfinance가 설치되지 않았습니다. pip install yfinance 또는 --synthetic 사용 |
| 5 | AMZN | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | yfinance가 설치되지 않았습니다. pip install yfinance 또는 --synthetic 사용 |

## Validation details

### AAPL / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — yfinance가 설치되지 않았습니다. pip install yfinance 또는 --synthetic 사용

### AAPL / Track-S / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — yfinance가 설치되지 않았습니다. pip install yfinance 또는 --synthetic 사용

### AMD / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — yfinance가 설치되지 않았습니다. pip install yfinance 또는 --synthetic 사용

### AMD / Track-S / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — yfinance가 설치되지 않았습니다. pip install yfinance 또는 --synthetic 사용

### AMZN / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — yfinance가 설치되지 않았습니다. pip install yfinance 또는 --synthetic 사용
