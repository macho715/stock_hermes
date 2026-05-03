# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-02T18:10:58+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, AMD, AVGO, GOOGL, AMZN, META, TSLA, JPM, XOM, LLY, UNH, COST, QQQ, SPY, XLK, XLE, GLD
Track: BOTH | Period: 3y | Top-N: 10

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | XOM | L | ACCUMULATE_RECOMMENDATION | 100.00 | 92.45% | 17.59 | 152.75 | 134.42 | 183.30 | 1.67 | 0.50% | 12.00% | 27.28 | 8/9 | data_source=yfinance; cv_gap=5; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 2 | NVDA | L | ACCUMULATE_RECOMMENDATION | 100.00 | 84.30% | 14.98 | 198.45 | 174.64 | 238.14 | 1.67 | 0.50% | 12.00% | 21.00 | 8/9 | data_source=yfinance; cv_gap=5; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 3 | XLE | L | ACCUMULATE_RECOMMENDATION | 100.00 | 77.50% | 12.80 | 58.85 | 51.79 | 70.62 | 1.67 | 0.50% | 12.00% | 70.80 | 8/9 | data_source=yfinance; cv_gap=5; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 4 | QQQ | S | ELIGIBLE_RECOMMENDATION | 100.00 | 96.46% | 9.50 | 674.15 | 647.18 | 741.57 | 2.50 | 0.75% | 20.00% | 27.81 | 8/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 96.46%; 단기/중기 추세 확인 |
| 5 | AAPL | S | ELIGIBLE_RECOMMENDATION | 100.00 | 95.93% | 9.43 | 280.14 | 268.93 | 308.15 | 2.50 | 0.75% | 20.00% | 66.93 | 9/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 95.93%; 단기/중기 추세 확인 |
| 6 | XLK | S | ELIGIBLE_RECOMMENDATION | 100.00 | 94.23% | 9.19 | 161.87 | 155.40 | 178.06 | 2.50 | 0.75% | 20.00% | 115.83 | 8/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 94.23%; 단기/중기 추세 확인 |
| 7 | JPM | S | ELIGIBLE_RECOMMENDATION | 100.00 | 92.30% | 8.92 | 312.47 | 299.97 | 343.72 | 2.50 | 0.75% | 20.00% | 60.01 | 9/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 92.30%; 단기/중기 추세 확인 |
| 8 | GOOGL | S | ELIGIBLE_RECOMMENDATION | 100.00 | 84.14% | 7.78 | 385.69 | 370.26 | 424.26 | 2.50 | 0.75% | 20.00% | 48.61 | 9/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 84.14%; 단기/중기 추세 확인 |
| 9 | AVGO | S | ELIGIBLE_RECOMMENDATION | 98.64 | 95.10% | 9.31 | 421.28 | 404.01 | 463.41 | 2.44 | 0.75% | 20.00% | 43.43 | 8/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 95.10%; 단기/중기 추세 확인 |
| 10 | AVGO | L | ACCUMULATE_RECOMMENDATION | 98.45 | 97.63% | 19.24 | 421.28 | 370.73 | 505.54 | 1.67 | 0.50% | 12.00% | 9.89 | 9/9 | data_source=yfinance; cv_gap=5; 장기 추세 구조 양호; 장기 MDD 한도 내 |

## Validation details

### XOM / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.30%, Sharpe=0.294, Sortino=0.285, MDD=0.58%
- Model: prob=92.45%, acc=48.32%, auc=0.636, oof_coverage=74.83%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=2849546898.11
- MARKET_REGIME: PASS — regime_score=65.00, atr_pct=0.0290
- MODEL_EDGE: AMBER — prob=0.9245, acc=0.4832, auc=0.6357, models=xgb-cuda
- OOF_COVERAGE: PASS — coverage=74.83%, gap=5
- BACKTEST_SANITY: PASS — return=0.30%, sharpe=0.294, mdd=0.58%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### NVDA / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.34%, Sharpe=0.128, Sortino=0.130, MDD=1.86%
- Model: prob=84.30%, acc=40.98%, auc=0.706, oof_coverage=74.83%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=29203206405.88
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0316
- MODEL_EDGE: AMBER — prob=0.8430, acc=0.4098, auc=0.7056, models=xgb-cuda
- OOF_COVERAGE: PASS — coverage=74.83%, gap=5
- BACKTEST_SANITY: PASS — return=0.34%, sharpe=0.128, mdd=1.86%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### XLE / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.17%, Sharpe=0.198, Sortino=0.136, MDD=0.40%
- Model: prob=77.50%, acc=38.23%, auc=0.748, oof_coverage=74.83%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=2532175196.71
- MARKET_REGIME: PASS — regime_score=85.00, atr_pct=0.0238
- MODEL_EDGE: AMBER — prob=0.7750, acc=0.3823, auc=0.7483, models=xgb-cuda
- OOF_COVERAGE: PASS — coverage=74.83%, gap=5
- BACKTEST_SANITY: PASS — return=0.17%, sharpe=0.198, mdd=0.40%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.63%, Sharpe=0.207, Sortino=0.198, MDD=2.64%
- Model: prob=96.46%, acc=45.00%, auc=0.600, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=26333511708.52
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0146
- MODEL_EDGE: AMBER — prob=0.9646, acc=0.4500, auc=0.6001, models=xgb-cuda
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=0.63%, sharpe=0.207, mdd=2.64%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AAPL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.65%, Sharpe=-0.231, Sortino=-0.189, MDD=2.78%
- Model: prob=95.93%, acc=64.17%, auc=0.638, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12232704966.48
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0236
- MODEL_EDGE: PASS — prob=0.9593, acc=0.6417, auc=0.6384, models=xgb-cuda
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=-0.65%, sharpe=-0.231, mdd=2.78%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### XLK / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.48%, Sharpe=-0.135, Sortino=-0.109, MDD=2.99%
- Model: prob=94.23%, acc=43.61%, auc=0.622, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=1564678515.88
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0186
- MODEL_EDGE: AMBER — prob=0.9423, acc=0.4361, auc=0.6221, models=xgb-cuda
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=-0.48%, sharpe=-0.135, mdd=2.99%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### JPM / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=1.53%, Sharpe=0.595, Sortino=0.644, MDD=1.10%
- Model: prob=92.30%, acc=65.00%, auc=0.662, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=2495547360.76
- MARKET_REGIME: PASS — regime_score=85.00, atr_pct=0.0194
- MODEL_EDGE: PASS — prob=0.9230, acc=0.6500, auc=0.6621, models=xgb-cuda
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=1.53%, sharpe=0.595, mdd=1.10%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### GOOGL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=2.90%, Sharpe=1.028, Sortino=0.971, MDD=1.01%
- Model: prob=84.14%, acc=55.56%, auc=0.586, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=9178084949.60
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0260
- MODEL_EDGE: PASS — prob=0.8414, acc=0.5556, auc=0.5861, models=xgb-cuda
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=2.90%, sharpe=1.028, mdd=1.01%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AVGO / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=1.84%, Sharpe=0.370, Sortino=0.450, MDD=3.54%
- Model: prob=95.10%, acc=34.72%, auc=0.688, oof_coverage=75.00%
- Risk plan: stop=4.10%, tp2=10.00%, R/R=2.44, position_value=18298.20
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=8479723534.32
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0304
- MODEL_EDGE: AMBER — prob=0.9510, acc=0.3472, auc=0.6882, models=xgb-cuda
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=1.84%, sharpe=0.370, mdd=3.54%
- RISK_PLAN: PASS — stop_pct=4.10%, tp2_pct=10.00%, rr=2.44, risk_budget=0.75%
- TRACK_SCORE: PASS — score=98.64, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AVGO / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=2.41%, Sharpe=0.704, Sortino=0.838, MDD=2.10%
- Model: prob=97.63%, acc=50.46%, auc=0.661, oof_coverage=74.83%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=8479723534.32
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0304
- MODEL_EDGE: PASS — prob=0.9763, acc=0.5046, auc=0.6614, models=xgb-cuda
- OOF_COVERAGE: PASS — coverage=74.83%, gap=5
- BACKTEST_SANITY: PASS — return=2.41%, sharpe=0.704, mdd=2.10%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=98.45, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
