# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-06T17:06:48+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, SPY, QQQ
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_recommend_us\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | GOOGL | S | ELIGIBLE_RECOMMENDATION | 100.00 | 87.39% | 8.23 | 399.31 | 383.33 | 439.24 | 2.50 | 0.75% | 20.00% | 46.96 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 87.39%; 단기/중기 추세 확인 |
| 2 | AAPL | S | ELIGIBLE_RECOMMENDATION | 100.00 | 83.89% | 7.74 | 286.09 | 274.65 | 314.70 | 2.50 | 0.75% | 20.00% | 65.54 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 83.89%; 단기/중기 추세 확인 |
| 3 | AMZN | L | ACCUMULATE_RECOMMENDATION | 99.91 | 77.31% | 12.74 | 275.89 | 242.78 | 331.07 | 1.67 | 0.50% | 12.00% | 15.10 | 9/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 장기 MDD 한도 내 |
| 4 | NVDA | L | ACCUMULATE_RECOMMENDATION | 99.01 | 96.02% | 18.73 | 204.89 | 180.30 | 245.87 | 1.67 | 0.50% | 12.00% | 20.34 | 8/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 5 | QQQ | S | ELIGIBLE_RECOMMENDATION | 98.47 | 92.90% | 9.01 | 691.86 | 664.19 | 761.05 | 2.50 | 0.75% | 20.00% | 27.10 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 92.90%; 단기/중기 추세 확인 |

## Validation details

### GOOGL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.77%, Sharpe=0.384, Sortino=0.287, MDD=1.01%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=87.39%, acc=45.10%, auc=0.581, oof_coverage=74.53%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=9333068451.13
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0249
- MODEL_EDGE: AMBER — prob=0.8739, acc=0.4510, auc=0.5805, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.53%, gap=20
- BACKTEST_SANITY: PASS — return=0.77%, sharpe=0.384, mdd=1.01%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AAPL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-1.28%, Sharpe=-0.443, Sortino=-0.337, MDD=3.25%
- Backtest honesty: AMBER (pass=3, amber=2, fail=0)
- Model: prob=83.89%, acc=63.87%, auc=0.647, oof_coverage=74.53%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12234371109.63
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0231
- MODEL_EDGE: PASS — prob=0.8389, acc=0.6387, auc=0.6470, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.53%, gap=20
- BACKTEST_SANITY: AMBER — return=-1.28%, sharpe=-0.443, mdd=3.25%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AMZN / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=1.13%, Sharpe=0.646, Sortino=0.615, MDD=0.83%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=77.31%, acc=62.08%, auc=0.690, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12911367760.63
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0260
- MODEL_EDGE: PASS — prob=0.7731, acc=0.6208, auc=0.6903, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=1.13%, sharpe=0.646, mdd=0.83%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=99.91, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### NVDA / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.27%, Sharpe=0.115, Sortino=0.091, MDD=1.85%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=96.02%, acc=33.03%, auc=0.499, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=29131293771.09
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0317
- MODEL_EDGE: AMBER — prob=0.9602, acc=0.3303, auc=0.4993, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=0.27%, sharpe=0.115, mdd=1.85%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=99.01, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.34%, Sharpe=-0.110, Sortino=-0.092, MDD=2.58%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=92.90%, acc=34.17%, auc=0.567, oof_coverage=74.53%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=25077947827.22
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0142
- MODEL_EDGE: AMBER — prob=0.9290, acc=0.3417, auc=0.5672, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.53%, gap=20
- BACKTEST_SANITY: PASS — return=-0.34%, sharpe=-0.110, mdd=2.58%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=98.47, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
