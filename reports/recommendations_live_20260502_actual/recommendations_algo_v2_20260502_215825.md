# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-02T17:58:25+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, AMD, AVGO, GOOGL, AMZN, META, TSLA, JPM, XOM, LLY, UNH, COST, QQQ, SPY, XLK, XLE, GLD
Track: BOTH | Period: 3y | Top-N: 5

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | XLE | L | ACCUMULATE_RECOMMENDATION | 100.00 | 93.52% | 17.93 | 58.85 | 51.79 | 70.62 | 1.67 | 0.50% | 12.00% | 70.80 | 9/9 | data_source=yfinance; cv_gap=5; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 2 | AMZN | S | ELIGIBLE_RECOMMENDATION | 100.00 | 99.24% | 9.89 | 268.26 | 257.53 | 295.09 | 2.50 | 0.75% | 20.00% | 69.89 | 9/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 99.24%; 단기/중기 추세 확인 |
| 3 | QQQ | S | ELIGIBLE_RECOMMENDATION | 100.00 | 98.54% | 9.80 | 674.15 | 647.18 | 741.57 | 2.50 | 0.75% | 20.00% | 27.81 | 8/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 98.54%; 단기/중기 추세 확인 |
| 4 | AVGO | S | ELIGIBLE_RECOMMENDATION | 100.00 | 87.03% | 8.17 | 421.28 | 404.01 | 463.41 | 2.44 | 0.75% | 20.00% | 43.43 | 8/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 87.03%; 단기/중기 추세 확인 |
| 5 | GOOGL | S | ELIGIBLE_RECOMMENDATION | 100.00 | 63.14% | 4.84 | 385.69 | 370.26 | 424.26 | 2.50 | 0.75% | 20.00% | 48.61 | 9/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 63.14%; 단기/중기 추세 확인 |

## Validation details

### XLE / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.29%, Sharpe=0.375, Sortino=0.347, MDD=0.80%
- Model: prob=93.52%, acc=63.30%, auc=0.835, oof_coverage=74.83%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=2532175196.71
- MARKET_REGIME: PASS — regime_score=85.00, atr_pct=0.0238
- MODEL_EDGE: PASS — prob=0.9352, acc=0.6330, auc=0.8350, models=logistic
- OOF_COVERAGE: PASS — coverage=74.83%, gap=5
- BACKTEST_SANITY: PASS — return=0.29%, sharpe=0.375, mdd=0.80%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AMZN / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=1.56%, Sharpe=0.710, Sortino=0.604, MDD=2.09%
- Model: prob=99.24%, acc=52.22%, auc=0.630, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12506253745.01
- MARKET_REGIME: PASS — regime_score=85.00, atr_pct=0.0279
- MODEL_EDGE: PASS — prob=0.9924, acc=0.5222, auc=0.6305, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=1.56%, sharpe=0.710, mdd=2.09%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.79%, Sharpe=0.268, Sortino=0.254, MDD=2.58%
- Model: prob=98.54%, acc=42.78%, auc=0.613, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=26333511708.52
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0146
- MODEL_EDGE: AMBER — prob=0.9854, acc=0.4278, auc=0.6131, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=0.79%, sharpe=0.268, mdd=2.58%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AVGO / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=7.65%, Sharpe=1.028, Sortino=1.014, MDD=4.24%
- Model: prob=87.03%, acc=43.33%, auc=0.699, oof_coverage=75.00%
- Risk plan: stop=4.10%, tp2=10.00%, R/R=2.44, position_value=18298.20
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=8479723534.32
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0304
- MODEL_EDGE: AMBER — prob=0.8703, acc=0.4333, auc=0.6985, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=7.65%, sharpe=1.028, mdd=4.24%
- RISK_PLAN: PASS — stop_pct=4.10%, tp2_pct=10.00%, rr=2.44, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### GOOGL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=3.73%, Sharpe=1.299, Sortino=0.809, MDD=1.01%
- Model: prob=63.14%, acc=54.72%, auc=0.720, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=9178084949.60
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0260
- MODEL_EDGE: PASS — prob=0.6314, acc=0.5472, auc=0.7203, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=3.73%, sharpe=1.299, mdd=1.01%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
