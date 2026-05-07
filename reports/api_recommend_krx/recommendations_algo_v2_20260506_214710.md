# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-06T17:47:10+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: 005930.KS, 000660.KS, 005380.KS, 005490.KS, 035420.KS, 035720.KS, 051910.KS, 006400.KS, 003670.KS
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_recommend_krx\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 003670.KS | S | ELIGIBLE_RECOMMENDATION | 95.02 | 92.11% | 8.82 | 267000.00 | 253650.00 | 293700.00 | 2.00 | 0.75% | 20.00% | 0.06 | 7/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 92.11%; 단기/중기 추세 확인 |
| 2 | 000660.KS | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | 000660.KS: yfinance provider failed: empty OHLCV frame |
| 3 | 000660.KS | S | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | 000660.KS: yfinance provider failed: empty OHLCV frame |
| 4 | 003670.KS | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | target class가 하나뿐이라 분류 모델을 학습할 수 없습니다 |
| 5 | 005380.KS | L | RED_DATA_OR_MODEL_ERROR | 0.00 | 0.00% | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00% | 0.00% | 0.00 | 0/1 | 005380.KS: yfinance provider failed: empty OHLCV frame |

## Validation details

### 003670.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-2.34%, Sharpe=-0.800, Sortino=-0.390, MDD=2.89%
- Backtest honesty: AMBER (pass=3, amber=2, fail=0)
- Model: prob=92.11%, acc=39.82%, auc=0.577, oof_coverage=74.67%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=727, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=90070256575.00
- MARKET_REGIME: PASS — regime_score=95.00, atr_pct=0.0503
- MODEL_EDGE: AMBER — prob=0.9211, acc=0.3982, auc=0.5770, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.67%, gap=20
- BACKTEST_SANITY: AMBER — return=-2.34%, sharpe=-0.800, mdd=2.89%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=95.02, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

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
- ERROR: FAIL — target class가 하나뿐이라 분류 모델을 학습할 수 없습니다

### 005380.KS / Track-L / RED_DATA_OR_MODEL_ERROR
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: FAIL (pass=0, amber=0, fail=1)
- Model: prob=0.00%, acc=0.00%, auc=0.000, oof_coverage=0.00%
- Risk plan: stop=0.00%, tp2=0.00%, R/R=0.00, position_value=0.00
- ERROR: FAIL — 005380.KS: yfinance provider failed: empty OHLCV frame
