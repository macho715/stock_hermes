# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-06T20:25:38+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: 005930.KS, 000660.KS, 005380.KS, 005490.KS, 035420.KS, 035720.KS, 051910.KS, 006400.KS, 003670.KS
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_recommend_krx\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 000660.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 96.20% | 9.43 | 1601000.00 | 1520950.00 | 1761100.00 | 2.00 | 0.75% | 20.00% | 0.01 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 96.20%; 단기/중기 추세 확인 |
| 2 | 005490.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 87.62% | 8.14 | 506000.00 | 480700.00 | 556600.00 | 2.00 | 0.75% | 20.00% | 0.03 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 87.62%; 단기/중기 추세 확인 |
| 3 | 005380.KS | S | ELIGIBLE_RECOMMENDATION | 99.87 | 90.36% | 8.55 | 550000.00 | 522500.00 | 605000.00 | 2.00 | 0.75% | 20.00% | 0.03 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 90.36%; 단기/중기 추세 확인 |
| 4 | 006400.KS | L | ACCUMULATE_RECOMMENDATION | 99.81 | 97.01% | 19.04 | 698000.00 | 614240.00 | 837600.00 | 1.67 | 0.50% | 12.00% | 0.01 | 8/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 5 | 005930.KS | S | ELIGIBLE_RECOMMENDATION | 99.52 | 96.51% | 9.48 | 266000.00 | 252700.00 | 292600.00 | 2.00 | 0.75% | 20.00% | 0.06 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 96.51%; 단기/중기 추세 확인 |

## Validation details

### 000660.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.59%, Sharpe=0.182, Sortino=0.144, MDD=2.33%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=96.20%, acc=46.31%, auc=0.740, oof_coverage=74.67%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=4909187084800.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0450
- MODEL_EDGE: AMBER — prob=0.9620, acc=0.4631, auc=0.7400, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.67%, gap=20
- BACKTEST_SANITY: PASS — return=0.59%, sharpe=0.182, mdd=2.33%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005490.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.64%, Sharpe=0.173, Sortino=0.130, MDD=2.72%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=87.62%, acc=40.41%, auc=0.687, oof_coverage=74.51%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=235337044575.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0395
- MODEL_EDGE: AMBER — prob=0.8762, acc=0.4041, auc=0.6870, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.51%, gap=20
- BACKTEST_SANITY: PASS — return=0.64%, sharpe=0.173, mdd=2.72%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005380.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=2.46%, Sharpe=0.692, Sortino=0.822, MDD=1.43%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=90.36%, acc=37.46%, auc=0.590, oof_coverage=74.51%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=562002585075.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0464
- MODEL_EDGE: AMBER — prob=0.9036, acc=0.3746, auc=0.5896, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.51%, gap=20
- BACKTEST_SANITY: PASS — return=2.46%, sharpe=0.692, mdd=1.43%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=99.87, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 006400.KS / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.00%, Sharpe=0.000, Sortino=0.000, MDD=0.00%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=97.01%, acc=36.25%, auc=0.454, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=578773496775.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0479
- MODEL_EDGE: AMBER — prob=0.9701, acc=0.3625, auc=0.4539, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=0.00%, sharpe=0.000, mdd=0.00%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=99.81, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005930.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=1.19%, Sharpe=0.580, Sortino=0.455, MDD=0.96%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=96.51%, acc=33.63%, auc=0.590, oof_coverage=74.51%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=5602731199675.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0421
- MODEL_EDGE: AMBER — prob=0.9651, acc=0.3363, auc=0.5900, models=xgb-cpu
- OOF_COVERAGE: PASS — coverage=74.51%, gap=20
- BACKTEST_SANITY: PASS — return=1.19%, sharpe=0.580, mdd=0.96%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=99.52, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
