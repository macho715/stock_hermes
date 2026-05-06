# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-06T17:24:29+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: 005930.KS, 000660.KS, 005380.KS, 005490.KS, 035420.KS, 035720.KS, 051910.KS, 006400.KS, 003670.KS
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_recommend_krx\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 005930.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 96.12% | 9.42 | 232500.00 | 220875.00 | 255750.00 | 2.00 | 0.75% | 20.00% | 0.06 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 96.12%; 단기/중기 추세 확인 |
| 2 | 000660.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 95.81% | 9.37 | 1447000.00 | 1374650.00 | 1591700.00 | 2.00 | 0.75% | 20.00% | 0.01 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 95.81%; 단기/중기 추세 확인 |
| 3 | 005490.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 87.83% | 8.17 | 502000.00 | 476900.00 | 552200.00 | 2.00 | 0.75% | 20.00% | 0.03 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 87.83%; 단기/중기 추세 확인 |
| 4 | 005380.KS | L | ACCUMULATE_RECOMMENDATION | 99.55 | 90.94% | 17.10 | 539000.00 | 474320.00 | 646800.00 | 1.67 | 0.50% | 12.00% | 0.01 | 8/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 5 | 005490.KS | L | ACCUMULATE_RECOMMENDATION | 97.86 | 94.20% | 18.14 | 502000.00 | 441760.00 | 602400.00 | 1.67 | 0.50% | 12.00% | 0.01 | 7/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 장기 MDD 한도 내 |

## Validation details

### 005930.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=1.20%, Sharpe=0.585, Sortino=0.457, MDD=0.96%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=96.12%, acc=33.63%, auc=0.592, oof_coverage=74.67%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=727, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=5095768027365.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0395
- MODEL_EDGE: AMBER — prob=0.9612, acc=0.3363, auc=0.5923, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.67%, gap=20
- BACKTEST_SANITY: PASS — return=1.20%, sharpe=0.585, mdd=0.96%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 000660.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.82%, Sharpe=0.245, Sortino=0.196, MDD=2.33%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=95.81%, acc=46.31%, auc=0.761, oof_coverage=74.83%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=727, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=4515674580800.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0447
- MODEL_EDGE: AMBER — prob=0.9581, acc=0.4631, auc=0.7606, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.83%, gap=20
- BACKTEST_SANITY: PASS — return=0.82%, sharpe=0.245, mdd=2.33%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005490.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.53%, Sharpe=0.145, Sortino=0.109, MDD=2.72%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=87.83%, acc=41.00%, auc=0.675, oof_coverage=74.67%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=727, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=224680495525.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0396
- MODEL_EDGE: AMBER — prob=0.8783, acc=0.4100, auc=0.6746, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.67%, gap=20
- BACKTEST_SANITY: PASS — return=0.53%, sharpe=0.145, mdd=2.72%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005380.KS / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=90.94%, acc=24.84%, auc=0.475, oof_coverage=74.45%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=727, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=528482361725.00
- MARKET_REGIME: PASS — regime_score=85.00, atr_pct=0.0474
- MODEL_EDGE: AMBER — prob=0.9094, acc=0.2484, auc=0.4750, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.45%, gap=63
- BACKTEST_SANITY: PASS — return=0.00%, sharpe=0.000, mdd=0.00%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=99.55, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005490.KS / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=-0.46%, Sharpe=-0.458, Sortino=-0.204, MDD=0.87%
- Backtest honesty: AMBER (pass=3, amber=2, fail=0)
- Model: prob=94.20%, acc=32.68%, auc=0.723, oof_coverage=74.45%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=727, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=224680495525.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0396
- MODEL_EDGE: AMBER — prob=0.9420, acc=0.3268, auc=0.7232, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.45%, gap=63
- BACKTEST_SANITY: AMBER — return=-0.46%, sharpe=-0.458, mdd=0.87%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=97.86, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
