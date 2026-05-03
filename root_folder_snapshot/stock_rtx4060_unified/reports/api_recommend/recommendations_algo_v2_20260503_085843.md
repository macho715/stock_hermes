# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-03T04:58:43+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, AMD, AVGO, GOOGL, AMZN, META, TSLA, JPM, XOM, LLY, UNH, COST, QQQ, SPY, XLK, XLE, GLD
Track: BOTH | Period: 3y | Top-N: 5
Data provider: auto | Synthetic flag: False
Audit log: reports\api_recommend\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | XLE | L | ACCUMULATE_RECOMMENDATION | 100.00 | 93.52% | 17.93 | 58.85 | 51.79 | 70.62 | 1.67 | 0.50% | 12.00% | 70.80 | 9/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 2 | QQQ | S | ELIGIBLE_RECOMMENDATION | 100.00 | 98.57% | 9.80 | 674.15 | 647.18 | 741.57 | 2.50 | 0.75% | 20.00% | 27.81 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 98.57%; 단기/중기 추세 확인 |
| 3 | XLK | S | ELIGIBLE_RECOMMENDATION | 100.00 | 94.21% | 9.19 | 161.87 | 155.40 | 178.06 | 2.50 | 0.75% | 20.00% | 115.83 | 7/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 94.21%; 단기/중기 추세 확인 |
| 4 | AVGO | S | ELIGIBLE_RECOMMENDATION | 100.00 | 87.07% | 8.18 | 421.28 | 404.01 | 463.41 | 2.44 | 0.75% | 20.00% | 43.43 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 87.07%; 단기/중기 추세 확인 |
| 5 | GOOGL | S | ELIGIBLE_RECOMMENDATION | 100.00 | 63.28% | 4.86 | 385.69 | 370.26 | 424.26 | 2.50 | 0.75% | 20.00% | 48.61 | 9/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 63.28%; 단기/중기 추세 확인 |

## Validation details

### XLE / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.03%, Sharpe=0.048, Sortino=0.032, MDD=0.62%
- Model: prob=93.52%, acc=57.49%, auc=0.834, oof_coverage=74.83%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=2532175196.71
- MARKET_REGIME: PASS — regime_score=85.00, atr_pct=0.0238
- MODEL_EDGE: PASS — prob=0.9352, acc=0.5749, auc=0.8335, models=logistic
- OOF_COVERAGE: PASS — coverage=74.83%, gap=63
- BACKTEST_SANITY: PASS — return=0.03%, sharpe=0.048, mdd=0.62%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.40%, Sharpe=-0.194, Sortino=-0.150, MDD=1.97%
- Model: prob=98.57%, acc=38.06%, auc=0.628, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=26333511708.52
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0146
- MODEL_EDGE: AMBER — prob=0.9857, acc=0.3806, auc=0.6280, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=20
- BACKTEST_SANITY: PASS — return=-0.40%, sharpe=-0.194, mdd=1.97%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### XLK / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-2.48%, Sharpe=-0.710, Sortino=-0.578, MDD=3.16%
- Model: prob=94.21%, acc=34.72%, auc=0.578, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=1564678515.88
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0186
- MODEL_EDGE: AMBER — prob=0.9421, acc=0.3472, auc=0.5775, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=20
- BACKTEST_SANITY: AMBER — return=-2.48%, sharpe=-0.710, mdd=3.16%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AVGO / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=8.39%, Sharpe=1.161, Sortino=1.042, MDD=4.67%
- Model: prob=87.07%, acc=45.56%, auc=0.673, oof_coverage=75.00%
- Risk plan: stop=4.10%, tp2=10.00%, R/R=2.44, position_value=18298.20
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=8479723534.32
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0304
- MODEL_EDGE: AMBER — prob=0.8707, acc=0.4556, auc=0.6735, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=20
- BACKTEST_SANITY: PASS — return=8.39%, sharpe=1.161, mdd=4.67%
- RISK_PLAN: PASS — stop_pct=4.10%, tp2_pct=10.00%, rr=2.44, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### GOOGL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=5.11%, Sharpe=1.730, Sortino=1.267, MDD=0.83%
- Model: prob=63.28%, acc=55.28%, auc=0.712, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=9178084949.60
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0260
- MODEL_EDGE: PASS — prob=0.6328, acc=0.5528, auc=0.7119, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=20
- BACKTEST_SANITY: PASS — return=5.11%, sharpe=1.730, mdd=0.83%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
