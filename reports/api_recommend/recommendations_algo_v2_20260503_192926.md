# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-03T15:29:26+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: SYNTH-A
Track: BOTH | Period: 3y | Top-N: 1
Data provider: auto | Synthetic flag: True
Audit log: reports\api_recommend\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | SYNTH-A | S | ELIGIBLE_RECOMMENDATION | 95.52 | 70.16% | 5.82 | 122.08 | 117.20 | 134.29 | 2.50 | 0.75% | 20.00% | 153.58 | 7/9 | data_source=synthetic_demo_data; cv_gap=20; 모델 상승확률 70.16%; 단기/중기 추세 확인 |

## Validation details

### SYNTH-A / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.46%, Sharpe=-0.299, Sortino=-0.253, MDD=1.00%
- Model: prob=70.16%, acc=41.87%, auc=0.531, oof_coverage=74.54%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=455582698.80
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0220
- MODEL_EDGE: AMBER — prob=0.7016, acc=0.4187, auc=0.5315, models=logistic
- OOF_COVERAGE: PASS — coverage=74.54%, gap=20
- BACKTEST_SANITY: AMBER — return=-0.46%, sharpe=-0.299, mdd=1.00%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=95.52, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
