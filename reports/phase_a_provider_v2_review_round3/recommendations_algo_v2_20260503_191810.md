# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-03T15:18:10+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: SYNTH-A, SYNTH-B
Track: BOTH | Period: 3y | Top-N: 2
Data provider: auto | Synthetic flag: True
Audit log: reports\phase_a_provider_v2_review_round3\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | SYNTH-A | S | ELIGIBLE_RECOMMENDATION | 95.05 | 70.16% | 5.82 | 122.08 | 117.20 | 134.29 | 2.50 | 0.75% | 20.00% | 153.58 | 7/9 | data_source=synthetic_demo_data; cv_gap=5; 모델 상승확률 70.16%; 단기/중기 추세 확인 |
| 2 | SYNTH-A | L | ACCUMULATE_RECOMMENDATION | 93.15 | 88.33% | 16.27 | 122.08 | 107.43 | 146.50 | 1.67 | 0.50% | 12.00% | 34.13 | 9/9 | data_source=synthetic_demo_data; cv_gap=5; 장기 추세 구조 양호; 장기 MDD 한도 내 |

## Validation details

### SYNTH-A / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.52%, Sharpe=-0.295, Sortino=-0.270, MDD=1.55%
- Model: prob=70.16%, acc=44.35%, auc=0.522, oof_coverage=74.54%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=455582698.80
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0220
- MODEL_EDGE: AMBER — prob=0.7016, acc=0.4435, auc=0.5223, models=logistic
- OOF_COVERAGE: PASS — coverage=74.54%, gap=5
- BACKTEST_SANITY: AMBER — return=-0.52%, sharpe=-0.295, mdd=1.55%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=95.05, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### SYNTH-A / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.46%, Sharpe=0.398, Sortino=0.490, MDD=0.64%
- Model: prob=88.33%, acc=52.25%, auc=0.382, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=455582698.80
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0220
- MODEL_EDGE: PASS — prob=0.8833, acc=0.5225, auc=0.3821, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=0.46%, sharpe=0.398, mdd=0.64%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=93.15, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
