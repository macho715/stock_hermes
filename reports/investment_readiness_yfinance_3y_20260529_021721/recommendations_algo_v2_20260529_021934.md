# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-28T22:19:34+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, SPY, QQQ
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\investment_readiness_yfinance_3y_20260529_021721\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | AAPL | S | ELIGIBLE_RECOMMENDATION | 100.00 | 94.05% | 9.17 | 312.51 | 300.01 | 343.76 | 2.50 | 0.75% | 20.00% | 60.00 | 9/9 | data_source=yfinance:cache; cv_gap=20; 모델 상승확률 94.05%; 단기/중기 추세 확인 |
| 2 | QQQ | S | ELIGIBLE_RECOMMENDATION | 99.82 | 97.89% | 9.71 | 735.60 | 706.18 | 809.16 | 2.50 | 0.75% | 20.00% | 25.49 | 8/9 | data_source=yfinance:cache; cv_gap=20; 모델 상승확률 97.89%; 단기/중기 추세 확인 |
| 3 | SPY | S | ELIGIBLE_RECOMMENDATION | 97.70 | 93.38% | 9.07 | 754.60 | 724.42 | 830.06 | 2.50 | 0.75% | 20.00% | 24.85 | 8/9 | data_source=yfinance:cache; cv_gap=20; 모델 상승확률 93.38%; 단기/중기 추세 확인 |
| 4 | QQQ | L | ACCUMULATE_RECOMMENDATION | 96.60 | 97.90% | 19.33 | 735.60 | 647.33 | 882.72 | 1.67 | 0.50% | 12.00% | 5.66 | 9/9 | data_source=yfinance:cache; cv_gap=43; 장기 추세 구조 양호; 장기 MDD 한도 내 |
| 5 | MSFT | S | ELIGIBLE_RECOMMENDATION | 93.72 | 73.58% | 6.30 | 426.99 | 409.91 | 469.69 | 2.50 | 0.75% | 20.00% | 43.91 | 8/9 | data_source=yfinance:cache; cv_gap=20; 모델 상승확률 73.58%; 단기/중기 추세 확인 |

## Validation details

### AAPL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.19%, Sharpe=0.114, Sortino=0.127, MDD=1.71%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=94.05%, acc=55.53%, auc=0.613, oof_coverage=100.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=14671628396.53
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0178
- MODEL_EDGE: PASS — prob=0.9405, acc=0.5553, auc=0.6134, models=logistic
- OOF_COVERAGE: PASS — coverage=100.00%, gap=20
- BACKTEST_SANITY: PASS — return=0.19%, sharpe=0.114, mdd=1.71%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.58%, Sharpe=0.473, Sortino=0.458, MDD=1.06%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=97.89%, acc=48.66%, auc=0.532, oof_coverage=100.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=27798568491.41
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0145
- MODEL_EDGE: AMBER — prob=0.9789, acc=0.4866, auc=0.5323, models=logistic
- OOF_COVERAGE: PASS — coverage=100.00%, gap=20
- BACKTEST_SANITY: PASS — return=0.58%, sharpe=0.473, mdd=1.06%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=99.82, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### SPY / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.74%, Sharpe=0.304, Sortino=0.270, MDD=1.87%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=93.38%, acc=45.54%, auc=0.483, oof_coverage=100.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=35030224158.73
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0095
- MODEL_EDGE: AMBER — prob=0.9338, acc=0.4554, auc=0.4827, models=logistic
- OOF_COVERAGE: PASS — coverage=100.00%, gap=20
- BACKTEST_SANITY: PASS — return=0.74%, sharpe=0.304, mdd=1.87%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=97.70, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.81%, Sharpe=0.551, Sortino=0.642, MDD=0.99%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=97.90%, acc=61.90%, auc=0.494, oof_coverage=100.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=27798568491.41
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0145
- MODEL_EDGE: PASS — prob=0.9790, acc=0.6190, auc=0.4939, models=logistic
- OOF_COVERAGE: PASS — coverage=100.00%, gap=43
- BACKTEST_SANITY: PASS — return=0.81%, sharpe=0.551, mdd=0.99%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=96.60, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### MSFT / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.06%, Sharpe=-0.024, Sortino=-0.023, MDD=1.06%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=73.58%, acc=47.19%, auc=0.500, oof_coverage=100.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=14304336788.18
- MARKET_REGIME: PASS — regime_score=65.00, atr_pct=0.0254
- MODEL_EDGE: AMBER — prob=0.7358, acc=0.4719, auc=0.5001, models=logistic
- OOF_COVERAGE: PASS — coverage=100.00%, gap=20
- BACKTEST_SANITY: PASS — return=-0.06%, sharpe=-0.024, mdd=1.06%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=93.72, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
