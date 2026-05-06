# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-05T05:18:22+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, SPY, QQQ
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_recommend_us\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | NVDA | L | ACCUMULATE_RECOMMENDATION | 100.00 | 77.56% | 12.82 | 198.48 | 174.66 | 238.18 | 1.67 | 0.50% | 12.00% | 20.99 | 7/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 2 | GOOGL | S | ELIGIBLE_RECOMMENDATION | 100.00 | 82.47% | 7.55 | 383.25 | 367.92 | 421.57 | 2.50 | 0.75% | 20.00% | 48.92 | 9/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 82.47%; 단기/중기 추세 확인 |
| 3 | SPY | S | ELIGIBLE_RECOMMENDATION | 97.65 | 99.84% | 9.98 | 718.01 | 689.29 | 789.81 | 2.50 | 0.75% | 20.00% | 26.11 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 99.84%; 단기/중기 추세 확인 |
| 4 | AMZN | S | ELIGIBLE_RECOMMENDATION | 96.94 | 99.55% | 9.94 | 272.05 | 261.17 | 299.25 | 2.50 | 0.75% | 20.00% | 68.92 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 99.55%; 단기/중기 추세 확인 |
| 5 | QQQ | S | ELIGIBLE_RECOMMENDATION | 96.63 | 99.39% | 9.91 | 672.88 | 645.96 | 740.17 | 2.50 | 0.75% | 20.00% | 27.87 | 7/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 99.39%; 단기/중기 추세 확인 |

## Validation details

### NVDA / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=-1.01%, Sharpe=-0.468, Sortino=-0.301, MDD=2.52%
- Backtest honesty: AMBER (pass=3, amber=2, fail=0)
- Model: prob=77.56%, acc=44.44%, auc=0.737, oof_coverage=74.48%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=751, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=29492608838.34
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0319
- MODEL_EDGE: AMBER — prob=0.7756, acc=0.4444, auc=0.7371, models=logistic
- OOF_COVERAGE: PASS — coverage=74.48%, gap=63
- BACKTEST_SANITY: AMBER — return=-1.01%, sharpe=-0.468, mdd=2.52%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### GOOGL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=2.54%, Sharpe=1.070, Sortino=0.721, MDD=0.83%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=82.47%, acc=55.18%, auc=0.739, oof_coverage=74.69%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=751, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=9427966906.88
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0257
- MODEL_EDGE: PASS — prob=0.8247, acc=0.5518, auc=0.7385, models=logistic
- OOF_COVERAGE: PASS — coverage=74.69%, gap=20
- BACKTEST_SANITY: PASS — return=2.54%, sharpe=1.070, mdd=0.83%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### SPY / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.12%, Sharpe=-0.039, Sortino=-0.034, MDD=2.08%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=99.84%, acc=35.85%, auc=0.613, oof_coverage=74.69%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=751, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=37983026146.26
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0108
- MODEL_EDGE: AMBER — prob=0.9984, acc=0.3585, auc=0.6133, models=logistic
- OOF_COVERAGE: PASS — coverage=74.69%, gap=20
- BACKTEST_SANITY: PASS — return=-0.12%, sharpe=-0.039, mdd=2.08%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=97.65, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AMZN / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.01%, Sharpe=-0.000, Sortino=-0.000, MDD=1.48%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=99.55%, acc=49.86%, auc=0.619, oof_coverage=74.69%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=751, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12903166960.75
- MARKET_REGIME: PASS — regime_score=85.00, atr_pct=0.0276
- MODEL_EDGE: AMBER — prob=0.9955, acc=0.4986, auc=0.6185, models=logistic
- OOF_COVERAGE: PASS — coverage=74.69%, gap=20
- BACKTEST_SANITY: PASS — return=-0.01%, sharpe=-0.000, mdd=1.48%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=96.94, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.89%, Sharpe=-0.396, Sortino=-0.292, MDD=2.48%
- Backtest honesty: AMBER (pass=3, amber=2, fail=0)
- Model: prob=99.39%, acc=41.18%, auc=0.606, oof_coverage=74.69%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=751, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=26463201644.37
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0144
- MODEL_EDGE: AMBER — prob=0.9939, acc=0.4118, auc=0.6060, models=logistic
- OOF_COVERAGE: PASS — coverage=74.69%, gap=20
- BACKTEST_SANITY: AMBER — return=-0.89%, sharpe=-0.396, mdd=2.48%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=96.63, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
