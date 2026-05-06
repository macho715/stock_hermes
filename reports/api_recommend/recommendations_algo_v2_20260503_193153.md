# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-03T15:31:53+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, AMD, AVGO, GOOGL, AMZN, META, TSLA, JPM, XOM, LLY, UNH, COST, QQQ, SPY, XLK, XLE, GLD
Track: BOTH | Period: 3y | Top-N: 5
Data provider: auto | Synthetic flag: False
Audit log: reports\api_recommend\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | XLE | L | ACCUMULATE_RECOMMENDATION | 100.00 | 92.12% | 17.48 | 58.85 | 51.79 | 70.62 | 1.67 | 0.50% | 12.00% | 70.80 | 9/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 2 | NVDA | L | ACCUMULATE_RECOMMENDATION | 100.00 | 78.22% | 13.03 | 198.45 | 174.64 | 238.14 | 1.67 | 0.50% | 12.00% | 21.00 | 7/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 3 | QQQ | S | ELIGIBLE_RECOMMENDATION | 100.00 | 99.89% | 9.98 | 674.15 | 647.18 | 741.57 | 2.50 | 0.75% | 20.00% | 27.81 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 99.89%; 단기/중기 추세 확인 |
| 4 | AVGO | S | ELIGIBLE_RECOMMENDATION | 100.00 | 87.28% | 8.21 | 421.28 | 404.01 | 463.41 | 2.44 | 0.75% | 20.00% | 43.43 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 87.28%; 단기/중기 추세 확인 |
| 5 | COST | S | ELIGIBLE_RECOMMENDATION | 99.80 | 75.81% | 6.61 | 1011.70 | 971.23 | 1112.87 | 2.50 | 0.75% | 20.00% | 18.53 | 9/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 75.81%; 단기/중기 추세 확인 |

## Validation details

### XLE / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.03%, Sharpe=0.067, Sortino=0.049, MDD=0.53%
- Model: prob=92.12%, acc=57.80%, auc=0.839, oof_coverage=74.83%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=2532175196.71
- MARKET_REGIME: PASS — regime_score=85.00, atr_pct=0.0238
- MODEL_EDGE: PASS — prob=0.9212, acc=0.5780, auc=0.8394, models=logistic
- OOF_COVERAGE: PASS — coverage=74.83%, gap=63
- BACKTEST_SANITY: PASS — return=0.03%, sharpe=0.067, mdd=0.53%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### NVDA / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=-1.16%, Sharpe=-0.536, Sortino=-0.347, MDD=2.70%
- Model: prob=78.22%, acc=45.57%, auc=0.745, oof_coverage=74.83%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=29203206405.88
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0316
- MODEL_EDGE: AMBER — prob=0.7822, acc=0.4557, auc=0.7446, models=logistic
- OOF_COVERAGE: PASS — coverage=74.83%, gap=63
- BACKTEST_SANITY: AMBER — return=-1.16%, sharpe=-0.536, mdd=2.70%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.06%, Sharpe=-0.032, Sortino=-0.027, MDD=1.59%
- Model: prob=99.89%, acc=40.56%, auc=0.590, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=26333511708.52
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0146
- MODEL_EDGE: AMBER — prob=0.9989, acc=0.4056, auc=0.5896, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=20
- BACKTEST_SANITY: PASS — return=-0.06%, sharpe=-0.032, mdd=1.59%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AVGO / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=8.32%, Sharpe=1.147, Sortino=1.118, MDD=4.09%
- Model: prob=87.28%, acc=45.00%, auc=0.692, oof_coverage=75.00%
- Risk plan: stop=4.10%, tp2=10.00%, R/R=2.44, position_value=18298.20
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=8479723534.32
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0304
- MODEL_EDGE: AMBER — prob=0.8728, acc=0.4500, auc=0.6922, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=20
- BACKTEST_SANITY: PASS — return=8.32%, sharpe=1.147, mdd=4.09%
- RISK_PLAN: PASS — stop_pct=4.10%, tp2_pct=10.00%, rr=2.44, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### COST / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.75%, Sharpe=0.416, Sortino=0.420, MDD=1.53%
- Model: prob=75.81%, acc=54.72%, auc=0.757, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=1765542867.15
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0183
- MODEL_EDGE: PASS — prob=0.7581, acc=0.5472, auc=0.7573, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=20
- BACKTEST_SANITY: PASS — return=0.75%, sharpe=0.416, mdd=1.53%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=99.80, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
