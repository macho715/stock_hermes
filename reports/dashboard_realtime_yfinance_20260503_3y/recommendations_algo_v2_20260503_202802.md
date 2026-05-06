# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-03T16:28:02+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, QQQ, SPY
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\dashboard_realtime_yfinance_20260503_3y\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | NVDA | L | ACCUMULATE_RECOMMENDATION | 100.00 | 78.23% | 13.04 | 198.45 | 174.64 | 238.14 | 1.67 | 0.50% | 12.00% | 21.00 | 8/9 | data_source=yfinance; cv_gap=5; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 2 | QQQ | S | ELIGIBLE_RECOMMENDATION | 100.00 | 99.89% | 9.98 | 674.15 | 647.18 | 741.57 | 2.50 | 0.75% | 20.00% | 27.81 | 8/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 99.89%; 단기/중기 추세 확인 |
| 3 | NVDA | S | ELIGIBLE_RECOMMENDATION | 97.46 | 69.55% | 5.66 | 198.45 | 189.97 | 218.29 | 2.34 | 0.75% | 20.00% | 88.48 | 7/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 69.55%; 단기/중기 추세 확인 |
| 4 | SPY | S | ELIGIBLE_RECOMMENDATION | 95.76 | 99.81% | 9.97 | 720.65 | 691.82 | 792.72 | 2.50 | 0.75% | 20.00% | 26.02 | 8/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 99.81%; 단기/중기 추세 확인 |
| 5 | QQQ | L | ACCUMULATE_RECOMMENDATION | 95.44 | 75.58% | 12.19 | 674.15 | 593.25 | 808.98 | 1.67 | 0.50% | 12.00% | 6.18 | 9/9 | data_source=yfinance; cv_gap=5; 장기 추세 구조 양호; 장기 MDD 한도 내 |

## Validation details

### NVDA / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=-0.33%, Sharpe=-0.118, Sortino=-0.097, MDD=1.86%
- Backtest honesty: AMBER (pass=3, amber=2, fail=0)
- Model: prob=78.23%, acc=34.56%, auc=0.680, oof_coverage=74.83%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=29203206405.88
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0316
- MODEL_EDGE: AMBER — prob=0.7823, acc=0.3456, auc=0.6797, models=logistic
- OOF_COVERAGE: PASS — coverage=74.83%, gap=5
- BACKTEST_SANITY: PASS — return=-0.33%, sharpe=-0.118, mdd=1.86%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.86%, Sharpe=0.289, Sortino=0.280, MDD=2.58%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=99.89%, acc=46.39%, auc=0.567, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=26333511708.52
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0146
- MODEL_EDGE: AMBER — prob=0.9989, acc=0.4639, auc=0.5669, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=0.86%, sharpe=0.289, mdd=2.58%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### NVDA / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-1.66%, Sharpe=-0.426, Sortino=-0.249, MDD=2.71%
- Backtest honesty: AMBER (pass=2, amber=3, fail=0)
- Model: prob=69.55%, acc=34.72%, auc=0.689, oof_coverage=75.00%
- Risk plan: stop=4.27%, tp2=10.00%, R/R=2.34, position_value=17558.95
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=29203206405.88
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0316
- MODEL_EDGE: AMBER — prob=0.6955, acc=0.3472, auc=0.6893, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: AMBER — return=-1.66%, sharpe=-0.426, mdd=2.71%
- RISK_PLAN: PASS — stop_pct=4.27%, tp2_pct=10.00%, rr=2.34, risk_budget=0.75%
- TRACK_SCORE: PASS — score=97.46, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### SPY / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.25%, Sharpe=0.094, Sortino=0.092, MDD=2.08%
- Backtest honesty: AMBER (pass=3, amber=2, fail=0)
- Model: prob=99.81%, acc=39.72%, auc=0.628, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=37403063079.81
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0108
- MODEL_EDGE: AMBER — prob=0.9981, acc=0.3972, auc=0.6276, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=0.25%, sharpe=0.094, mdd=2.08%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=95.76, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.43%, Sharpe=0.409, Sortino=0.392, MDD=0.90%
- Backtest honesty: AMBER (pass=3, amber=2, fail=0)
- Model: prob=75.58%, acc=53.82%, auc=0.427, oof_coverage=74.83%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=26333511708.52
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0146
- MODEL_EDGE: PASS — prob=0.7558, acc=0.5382, auc=0.4274, models=logistic
- OOF_COVERAGE: PASS — coverage=74.83%, gap=5
- BACKTEST_SANITY: PASS — return=0.43%, sharpe=0.409, mdd=0.90%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=95.44, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
