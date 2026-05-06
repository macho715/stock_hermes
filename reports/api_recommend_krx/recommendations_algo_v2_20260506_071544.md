# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-06T03:15:44+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: 005930.KS, 000660.KS, 005380.KS, 005490.KS, 035420.KS, 035720.KS, 051910.KS, 006400.KS, 003670.KS
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_recommend_krx\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 005380.KS | L | ACCUMULATE_RECOMMENDATION | 100.00 | 86.15% | 15.57 | 552000.00 | 485760.00 | 662400.00 | 1.67 | 0.50% | 12.00% | 0.01 | 9/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 2 | 051910.KS | L | ACCUMULATE_RECOMMENDATION | 100.00 | 70.58% | 10.59 | 421000.00 | 370480.00 | 505200.00 | 1.67 | 0.50% | 12.00% | 0.01 | 8/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 3 | 005930.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 99.98% | 10.00 | 261750.00 | 248662.50 | 287925.00 | 2.00 | 0.75% | 20.00% | 0.06 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 99.98%; 단기/중기 추세 확인 |
| 4 | 000660.KS | S | ELIGIBLE_RECOMMENDATION | 99.98 | 92.22% | 8.83 | 1588000.00 | 1508600.00 | 1746800.00 | 2.00 | 0.75% | 20.00% | 0.01 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 92.22%; 단기/중기 추세 확인 |
| 5 | 005490.KS | S | ELIGIBLE_RECOMMENDATION | 98.02 | 95.55% | 9.33 | 511000.00 | 485450.00 | 562100.00 | 2.00 | 0.75% | 20.00% | 0.03 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 95.55%; 단기/중기 추세 확인 |

## Validation details

### 005380.KS / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.90%, Sharpe=0.475, Sortino=0.641, MDD=1.09%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=86.15%, acc=59.87%, auc=0.663, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=545039268675.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0462
- MODEL_EDGE: PASS — prob=0.8615, acc=0.5987, auc=0.6635, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=0.90%, sharpe=0.475, mdd=1.09%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 051910.KS / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.05%, Sharpe=0.053, Sortino=0.035, MDD=0.76%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=70.58%, acc=44.98%, auc=0.728, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=127314453325.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0465
- MODEL_EDGE: AMBER — prob=0.7058, acc=0.4498, auc=0.7275, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=0.05%, sharpe=0.053, mdd=0.76%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005930.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=1.72%, Sharpe=0.521, Sortino=0.474, MDD=1.75%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=99.98%, acc=48.97%, auc=0.651, oof_coverage=74.51%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=5278803257875.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0409
- MODEL_EDGE: AMBER — prob=0.9998, acc=0.4897, auc=0.6513, models=logistic
- OOF_COVERAGE: PASS — coverage=74.51%, gap=20
- BACKTEST_SANITY: PASS — return=1.72%, sharpe=0.521, mdd=1.75%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 000660.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=2.19%, Sharpe=0.638, Sortino=0.527, MDD=2.33%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=92.22%, acc=47.79%, auc=0.823, oof_coverage=74.67%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=4663513269900.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0448
- MODEL_EDGE: AMBER — prob=0.9222, acc=0.4779, auc=0.8231, models=logistic
- OOF_COVERAGE: PASS — coverage=74.67%, gap=20
- BACKTEST_SANITY: PASS — return=2.19%, sharpe=0.638, mdd=2.33%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=99.98, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005490.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.69%, Sharpe=0.195, Sortino=0.148, MDD=3.01%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=95.55%, acc=46.02%, auc=0.687, oof_coverage=74.51%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=230701005775.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0391
- MODEL_EDGE: AMBER — prob=0.9555, acc=0.4602, auc=0.6870, models=logistic
- OOF_COVERAGE: PASS — coverage=74.51%, gap=20
- BACKTEST_SANITY: PASS — return=0.69%, sharpe=0.195, mdd=3.01%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=98.02, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
