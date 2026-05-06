# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-05T03:31:06+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: 005930.KS, 000660.KS
Track: BOTH | Period: 3y | Top-N: 3
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_recommend_krx_smoke\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 005930.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 100.00% | 10.00 | 232500.00 | 220875.00 | 255750.00 | 2.00 | 0.75% | 20.00% | 0.06 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 100.00%; 단기/중기 추세 확인 |
| 2 | 000660.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 83.64% | 7.55 | 1447000.00 | 1374650.00 | 1591700.00 | 2.00 | 0.75% | 20.00% | 0.01 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 83.64%; 단기/중기 추세 확인 |
| 3 | 005930.KS | L | ACCUMULATE_RECOMMENDATION | 97.43 | 99.99% | 20.00 | 232500.00 | 204600.00 | 279000.00 | 1.67 | 0.50% | 12.00% | 0.02 | 8/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 장기 MDD 한도 내 |

## Validation details

### 005930.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=1.07%, Sharpe=0.343, Sortino=0.306, MDD=2.09%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=100.00%, acc=48.67%, auc=0.643, oof_coverage=74.51%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=5095768027365.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0395
- MODEL_EDGE: AMBER — prob=1.0000, acc=0.4867, auc=0.6427, models=logistic
- OOF_COVERAGE: PASS — coverage=74.51%, gap=20
- BACKTEST_SANITY: PASS — return=1.07%, sharpe=0.343, mdd=2.09%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 000660.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=2.40%, Sharpe=0.686, Sortino=0.572, MDD=2.33%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=83.64%, acc=47.79%, auc=0.822, oof_coverage=74.67%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=4515674580800.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0447
- MODEL_EDGE: AMBER — prob=0.8364, acc=0.4779, auc=0.8222, models=logistic
- OOF_COVERAGE: PASS — coverage=74.67%, gap=20
- BACKTEST_SANITY: PASS — return=2.40%, sharpe=0.686, mdd=2.33%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### 005930.KS / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.73%, Sharpe=0.688, Sortino=0.484, MDD=0.42%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=99.99%, acc=39.48%, auc=0.660, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=728, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=5095768027365.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0395
- MODEL_EDGE: AMBER — prob=0.9999, acc=0.3948, auc=0.6603, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=0.73%, sharpe=0.688, mdd=0.42%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=97.43, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
