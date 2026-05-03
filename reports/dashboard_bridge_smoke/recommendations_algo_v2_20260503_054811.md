# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-03T01:48:11+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: SYNTH-A, SYNTH-B
Track: BOTH | Period: 3y | Top-N: 2
Data provider: auto | Synthetic flag: True
Audit log: reports\dashboard_bridge_smoke\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | SYNTH-A | S | ELIGIBLE_RECOMMENDATION | 99.10 | 73.67% | 6.31 | 122.08 | 117.20 | 134.29 | 2.50 | 0.75% | 20.00% | 153.58 | 8/9 | data_source=synthetic_demo_data; cv_gap=5; 모델 상승확률 73.67%; 단기/중기 추세 확인 |
| 2 | SYNTH-A | L | ACCUMULATE_RECOMMENDATION | 93.18 | 81.32% | 14.02 | 122.08 | 107.43 | 146.50 | 1.67 | 0.50% | 12.00% | 34.13 | 9/9 | data_source=synthetic_demo_data; cv_gap=5; 장기 추세 구조 양호; 장기 MDD 한도 내 |

## Validation details

### SYNTH-A / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.09%, Sharpe=-0.047, Sortino=-0.041, MDD=1.25%
- Model: prob=73.67%, acc=47.11%, auc=0.570, oof_coverage=74.54%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=455582698.80
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0220
- MODEL_EDGE: AMBER — prob=0.7367, acc=0.4711, auc=0.5699, models=logistic
- OOF_COVERAGE: PASS — coverage=74.54%, gap=5
- BACKTEST_SANITY: PASS — return=-0.09%, sharpe=-0.047, mdd=1.25%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=99.10, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### SYNTH-A / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.85%, Sharpe=0.717, Sortino=0.887, MDD=0.49%
- Model: prob=81.32%, acc=55.26%, auc=0.413, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=455582698.80
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0220
- MODEL_EDGE: PASS — prob=0.8132, acc=0.5526, auc=0.4127, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=0.85%, sharpe=0.717, mdd=0.49%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=93.18, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
