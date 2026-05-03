# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-02T18:18:22+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: SYNTH-A, SYNTH-B
Track: BOTH | Period: 3y | Top-N: 2

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | SYNTH-B | S | ELIGIBLE_RECOMMENDATION | 85.91 | 97.97% | 9.72 | 111.95 | 107.47 | 123.15 | 2.50 | 0.75% | 20.00% | 167.48 | 7/9 | data_source=synthetic_demo_data; cv_gap=5; 모델 상승확률 97.97%; 백테스트 MDD 0.98% |
| 2 | SYNTH-A | L | ACCUMULATE_RECOMMENDATION | 84.32 | 56.01% | 5.92 | 79.37 | 69.85 | 95.25 | 1.67 | 0.50% | 12.00% | 52.49 | 9/9 | data_source=synthetic_demo_data; cv_gap=5; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |

## Validation details

### SYNTH-B / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.83%, Sharpe=-0.603, Sortino=-0.473, MDD=0.98%
- Model: prob=97.97%, acc=52.89%, auc=0.622, oof_coverage=74.54%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=365898850.72
- MARKET_REGIME: AMBER — regime_score=30.00, atr_pct=0.0252
- MODEL_EDGE: PASS — prob=0.9797, acc=0.5289, auc=0.6218, models=logistic
- OOF_COVERAGE: PASS — coverage=74.54%, gap=5
- BACKTEST_SANITY: AMBER — return=-0.83%, sharpe=-0.603, mdd=0.98%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=85.91, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### SYNTH-A / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.15%, Sharpe=0.128, Sortino=0.141, MDD=0.88%
- Model: prob=56.01%, acc=52.85%, auc=0.597, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=315129826.77
- MARKET_REGIME: PASS — regime_score=65.00, atr_pct=0.0218
- MODEL_EDGE: PASS — prob=0.5601, acc=0.5285, auc=0.5966, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=0.15%, sharpe=0.128, mdd=0.88%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=84.32, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
