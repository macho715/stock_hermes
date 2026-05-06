# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-06T15:41:47+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, SPY, QQQ
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_recommend_us\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | NVDA | L | ACCUMULATE_RECOMMENDATION | 100.00 | 92.96% | 17.75 | 205.71 | 181.02 | 246.85 | 1.67 | 0.50% | 12.00% | 20.26 | 8/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 2 | QQQ | S | ELIGIBLE_RECOMMENDATION | 100.00 | 99.86% | 9.98 | 691.74 | 664.07 | 760.91 | 2.50 | 0.75% | 20.00% | 27.11 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 99.86%; 단기/중기 추세 확인 |
| 3 | SPY | S | ELIGIBLE_RECOMMENDATION | 100.00 | 99.80% | 9.97 | 731.64 | 702.37 | 804.80 | 2.50 | 0.75% | 20.00% | 25.63 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 99.80%; 단기/중기 추세 확인 |
| 4 | GOOGL | S | ELIGIBLE_RECOMMENDATION | 100.00 | 69.17% | 5.68 | 396.83 | 380.96 | 436.51 | 2.50 | 0.75% | 20.00% | 47.25 | 9/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 69.17%; 단기/중기 추세 확인 |
| 5 | AMZN | S | ELIGIBLE_RECOMMENDATION | 96.69 | 99.52% | 9.93 | 273.45 | 262.52 | 300.80 | 2.50 | 0.75% | 20.00% | 68.57 | 9/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 99.52%; 단기/중기 추세 확인 |

## Validation details

### NVDA / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=-0.38%, Sharpe=-0.183, Sortino=-0.134, MDD=1.69%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=92.96%, acc=44.95%, auc=0.736, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=28946197530.94
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0316
- MODEL_EDGE: AMBER — prob=0.9296, acc=0.4495, auc=0.7364, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=-0.38%, sharpe=-0.183, mdd=1.69%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.28%, Sharpe=-0.093, Sortino=-0.083, MDD=2.58%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=99.86%, acc=40.90%, auc=0.619, oof_coverage=74.53%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=24927828486.65
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0141
- MODEL_EDGE: AMBER — prob=0.9986, acc=0.4090, auc=0.6194, models=logistic
- OOF_COVERAGE: PASS — coverage=74.53%, gap=20
- BACKTEST_SANITY: PASS — return=-0.28%, sharpe=-0.093, mdd=2.58%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### SPY / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.10%, Sharpe=0.045, Sortino=0.038, MDD=2.10%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=99.80%, acc=35.57%, auc=0.634, oof_coverage=74.53%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=34419752748.48
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0106
- MODEL_EDGE: AMBER — prob=0.9980, acc=0.3557, auc=0.6340, models=logistic
- OOF_COVERAGE: PASS — coverage=74.53%, gap=20
- BACKTEST_SANITY: PASS — return=0.10%, sharpe=0.045, mdd=2.10%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### GOOGL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=1.71%, Sharpe=0.747, Sortino=0.456, MDD=1.21%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=69.17%, acc=53.78%, auc=0.740, oof_coverage=74.53%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=9257884372.90
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0248
- MODEL_EDGE: PASS — prob=0.6917, acc=0.5378, auc=0.7403, models=logistic
- OOF_COVERAGE: PASS — coverage=74.53%, gap=20
- BACKTEST_SANITY: PASS — return=1.71%, sharpe=0.747, mdd=1.21%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AMZN / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.39%, Sharpe=0.252, Sortino=0.185, MDD=1.48%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=99.52%, acc=50.14%, auc=0.631, oof_coverage=74.53%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12830680000.54
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0261
- MODEL_EDGE: PASS — prob=0.9952, acc=0.5014, auc=0.6306, models=logistic
- OOF_COVERAGE: PASS — coverage=74.53%, gap=20
- BACKTEST_SANITY: PASS — return=0.39%, sharpe=0.252, mdd=1.48%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=96.69, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
