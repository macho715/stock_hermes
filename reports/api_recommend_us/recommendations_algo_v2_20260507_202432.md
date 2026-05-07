# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-07T16:24:32+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, SPY, QQQ
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_recommend_us\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | AAPL | S | ELIGIBLE_RECOMMENDATION | 99.92 | 78.54% | 7.00 | 289.63 | 278.04 | 318.59 | 2.50 | 0.75% | 20.00% | 64.74 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 78.54%; 단기/중기 추세 확인 |
| 2 | AMZN | L | ACCUMULATE_RECOMMENDATION | 99.88 | 79.32% | 13.38 | 271.68 | 239.07 | 326.01 | 1.67 | 0.50% | 12.00% | 15.34 | 9/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 장기 MDD 한도 내 |
| 3 | QQQ | L | ACCUMULATE_RECOMMENDATION | 96.56 | 93.10% | 17.79 | 695.20 | 611.78 | 834.24 | 1.67 | 0.50% | 12.00% | 5.99 | 9/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 장기 MDD 한도 내 |
| 4 | SPY | S | ELIGIBLE_RECOMMENDATION | 96.43 | 96.03% | 9.44 | 732.50 | 703.20 | 805.75 | 2.50 | 0.75% | 20.00% | 25.60 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 96.03%; 단기/중기 추세 확인 |
| 5 | MSFT | S | ELIGIBLE_RECOMMENDATION | 95.97 | 96.06% | 9.45 | 424.34 | 407.36 | 466.77 | 2.50 | 0.75% | 20.00% | 44.19 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 96.06%; 단기/중기 추세 확인 |

## Validation details

### AAPL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-1.00%, Sharpe=-0.369, Sortino=-0.294, MDD=2.75%
- Backtest honesty: AMBER (pass=3, amber=2, fail=0)
- Model: prob=78.54%, acc=64.44%, auc=0.645, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12635752441.95
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0225
- MODEL_EDGE: PASS — prob=0.7854, acc=0.6444, auc=0.6455, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=75.00%, gap=20
- BACKTEST_SANITY: AMBER — return=-1.00%, sharpe=-0.369, mdd=2.75%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=99.92, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AMZN / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.98%, Sharpe=0.550, Sortino=0.520, MDD=0.73%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=79.32%, acc=62.69%, auc=0.700, oof_coverage=74.83%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12677391971.17
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0263
- MODEL_EDGE: PASS — prob=0.7932, acc=0.6269, auc=0.6995, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.83%, gap=63
- BACKTEST_SANITY: PASS — return=0.98%, sharpe=0.550, mdd=0.73%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=99.88, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.91%, Sharpe=0.701, Sortino=0.651, MDD=1.06%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=93.10%, acc=51.38%, auc=0.486, oof_coverage=74.83%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=25182726673.07
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0142
- MODEL_EDGE: PASS — prob=0.9310, acc=0.5138, auc=0.4858, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.83%, gap=63
- BACKTEST_SANITY: PASS — return=0.91%, sharpe=0.701, mdd=1.06%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=96.56, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### SPY / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.00%, Sharpe=0.006, Sortino=0.006, MDD=2.08%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=96.03%, acc=38.33%, auc=0.486, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=34579426945.15
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0105
- MODEL_EDGE: AMBER — prob=0.9603, acc=0.3833, auc=0.4862, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=75.00%, gap=20
- BACKTEST_SANITY: PASS — return=-0.00%, sharpe=0.006, mdd=2.08%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=96.43, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### MSFT / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.74%, Sharpe=0.304, Sortino=0.253, MDD=1.54%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=96.06%, acc=48.61%, auc=0.687, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=14322700682.04
- MARKET_REGIME: PASS — regime_score=65.00, atr_pct=0.0266
- MODEL_EDGE: AMBER — prob=0.9606, acc=0.4861, auc=0.6867, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=75.00%, gap=20
- BACKTEST_SANITY: PASS — return=0.74%, sharpe=0.304, mdd=1.54%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=95.97, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
