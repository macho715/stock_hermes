# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-05T03:56:07+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: 005930.KS, 000660.KS, 005380.KS, 005490.KS, 035420.KS, 035720.KS, 051910.KS, 006400.KS, 003670.KS
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_recommend_krx\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 005930.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 100.00% | 10.00 | 232500.00 | 220875.00 | 255750.00 | 2.00 | 0.75% | 20.00% | 0.06 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 100.00%; 단기/중기 추세 확인 |
| 2 | 005490.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 91.49% | 8.72 | 502000.00 | 476900.00 | 552200.00 | 2.00 | 0.75% | 20.00% | 0.03 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 91.49%; 단기/중기 추세 확인 |
| 3 | 000660.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 83.31% | 7.50 | 1447000.00 | 1374650.00 | 1591700.00 | 2.00 | 0.75% | 20.00% | 0.01 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 83.31%; 단기/중기 추세 확인 |
| 4 | 005380.KS | L | ACCUMULATE_RECOMMENDATION | 99.89 | 86.57% | 15.70 | 539000.00 | 474320.00 | 646800.00 | 1.67 | 0.50% | 12.00% | 0.01 | 9/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 5 | 005490.KS | L | ACCUMULATE_RECOMMENDATION | 97.68 | 99.98% | 20.00 | 502000.00 | 441760.00 | 602400.00 | 1.67 | 0.50% | 12.00% | 0.01 | 8/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 장기 MDD 한도 내 |

## Validation details

### 005930.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=1.07%, Sharpe=0.343, Sortino=0.306, MDD=2.09%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=100.00%, acc=48.97%, auc=0.644, oof_coverage=74.51%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=5095768027365.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0395
- MODEL_EDGE: AMBER — prob=1.0000, acc=0.4897, auc=0.6441, models=logistic
- OOF_COVERAGE: PASS — coverage=74.51%, gap=20
- BACKTEST_SANITY: PASS — return=1.07%, sharpe=0.343, mdd=2.09%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005490.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.46%, Sharpe=0.133, Sortino=0.097, MDD=3.25%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=91.49%, acc=45.43%, auc=0.685, oof_coverage=74.51%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=224680495525.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0396
- MODEL_EDGE: AMBER — prob=0.9149, acc=0.4543, auc=0.6850, models=logistic
- OOF_COVERAGE: PASS — coverage=74.51%, gap=20
- BACKTEST_SANITY: PASS — return=0.46%, sharpe=0.133, mdd=3.25%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 000660.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=2.40%, Sharpe=0.686, Sortino=0.573, MDD=2.33%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=83.31%, acc=47.79%, auc=0.820, oof_coverage=74.67%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=4515674580800.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0447
- MODEL_EDGE: AMBER — prob=0.8331, acc=0.4779, auc=0.8203, models=logistic
- OOF_COVERAGE: PASS — coverage=74.67%, gap=20
- BACKTEST_SANITY: PASS — return=2.40%, sharpe=0.686, mdd=2.33%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005380.KS / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.99%, Sharpe=0.516, Sortino=0.689, MDD=1.17%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=86.57%, acc=60.19%, auc=0.522, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=528482361725.00
- MARKET_REGIME: PASS — regime_score=85.00, atr_pct=0.0474
- MODEL_EDGE: PASS — prob=0.8657, acc=0.6019, auc=0.5217, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=0.99%, sharpe=0.516, mdd=1.17%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=99.89, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005490.KS / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=1.19%, Sharpe=0.664, Sortino=0.689, MDD=1.66%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=99.98%, acc=48.22%, auc=0.756, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=224680495525.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0396
- MODEL_EDGE: AMBER — prob=0.9998, acc=0.4822, auc=0.7561, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=1.19%, sharpe=0.664, mdd=1.66%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=97.68, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
