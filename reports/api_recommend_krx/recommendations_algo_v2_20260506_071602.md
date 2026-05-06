# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-06T03:16:02+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: 005930.KS, 000660.KS, 005380.KS, 005490.KS, 035420.KS, 035720.KS, 051910.KS, 006400.KS, 003670.KS
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_recommend_krx\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 005380.KS | L | ACCUMULATE_RECOMMENDATION | 100.00 | 85.69% | 15.42 | 552000.00 | 485760.00 | 662400.00 | 1.67 | 0.50% | 12.00% | 0.01 | 9/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 2 | 051910.KS | L | ACCUMULATE_RECOMMENDATION | 100.00 | 70.69% | 10.62 | 421000.00 | 370480.00 | 505200.00 | 1.67 | 0.50% | 12.00% | 0.01 | 8/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 3 | 005930.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 99.99% | 10.00 | 262000.00 | 248900.00 | 288200.00 | 2.00 | 0.75% | 20.00% | 0.06 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 99.99%; 단기/중기 추세 확인 |
| 4 | 000660.KS | S | ELIGIBLE_RECOMMENDATION | 99.98 | 92.21% | 8.83 | 1588000.00 | 1508600.00 | 1746800.00 | 2.00 | 0.75% | 20.00% | 0.01 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 92.21%; 단기/중기 추세 확인 |
| 5 | 005490.KS | S | ELIGIBLE_RECOMMENDATION | 98.25 | 95.56% | 9.34 | 510000.00 | 484500.00 | 561000.00 | 2.00 | 0.75% | 20.00% | 0.03 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 95.56%; 단기/중기 추세 확인 |

## Validation details

### 005380.KS / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.99%, Sharpe=0.532, Sortino=0.702, MDD=1.02%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=85.69%, acc=59.87%, auc=0.665, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=545047769475.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0462
- MODEL_EDGE: PASS — prob=0.8569, acc=0.5987, auc=0.6652, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=0.99%, sharpe=0.532, mdd=1.02%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 051910.KS / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.04%, Sharpe=0.045, Sortino=0.029, MDD=0.75%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=70.69%, acc=44.98%, auc=0.729, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=127315716325.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0465
- MODEL_EDGE: AMBER — prob=0.7069, acc=0.4498, auc=0.7293, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=0.04%, sharpe=0.045, mdd=0.75%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005930.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=1.94%, Sharpe=0.573, Sortino=0.524, MDD=1.75%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=99.99%, acc=49.56%, auc=0.652, oof_coverage=74.51%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=5279271902175.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0409
- MODEL_EDGE: AMBER — prob=0.9999, acc=0.4956, auc=0.6520, models=logistic
- OOF_COVERAGE: PASS — coverage=74.51%, gap=20
- BACKTEST_SANITY: PASS — return=1.94%, sharpe=0.573, mdd=1.75%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 000660.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=2.19%, Sharpe=0.638, Sortino=0.527, MDD=2.33%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=92.21%, acc=47.79%, auc=0.823, oof_coverage=74.67%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=4663608788100.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0448
- MODEL_EDGE: AMBER — prob=0.9221, acc=0.4779, auc=0.8232, models=logistic
- OOF_COVERAGE: PASS — coverage=74.67%, gap=20
- BACKTEST_SANITY: PASS — return=2.19%, sharpe=0.638, mdd=2.33%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=99.98, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005490.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.90%, Sharpe=0.249, Sortino=0.188, MDD=3.01%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=95.56%, acc=46.02%, auc=0.687, oof_coverage=74.51%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=230684807075.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0392
- MODEL_EDGE: AMBER — prob=0.9556, acc=0.4602, auc=0.6870, models=logistic
- OOF_COVERAGE: PASS — coverage=74.51%, gap=20
- BACKTEST_SANITY: PASS — return=0.90%, sharpe=0.249, mdd=3.01%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=98.25, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
