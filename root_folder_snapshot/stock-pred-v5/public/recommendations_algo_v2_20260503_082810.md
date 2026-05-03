# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-03T04:28:10+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: SYNTH-A, SYNTH-B, SYNTH-C
Track: BOTH | Period: 3y | Top-N: 3
Data provider: auto | Synthetic flag: True
Audit log: ..\stock-pred-v5\public\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | SYNTH-A | S | ELIGIBLE_RECOMMENDATION | 98.34 | 73.67% | 6.31 | 122.08 | 117.20 | 134.29 | 2.50 | 0.75% | 20.00% | 153.58 | 7/9 | data_source=synthetic_demo_data; cv_gap=20; 모델 상승확률 73.67%; 단기/중기 추세 확인 |
| 2 | SYNTH-A | L | ACCUMULATE_RECOMMENDATION | 93.19 | 81.32% | 14.02 | 122.08 | 107.43 | 146.50 | 1.67 | 0.50% | 12.00% | 34.13 | 9/9 | data_source=synthetic_demo_data; cv_gap=63; 장기 추세 구조 양호; 장기 MDD 한도 내 |
| 3 | SYNTH-C | S | RED_NOT_RECOMMENDED | 46.78 | 16.16% | -1.74 | 113.84 | 109.29 | 125.22 | 2.50 | 0.75% | 20.00% | 164.70 | 6/9 | data_source=synthetic_demo_data; cv_gap=20; 백테스트 MDD 0.97%; R/R 2.50 통과 |

## Validation details

### SYNTH-A / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.64%, Sharpe=-0.420, Sortino=-0.345, MDD=1.15%
- Model: prob=73.67%, acc=45.45%, auc=0.566, oof_coverage=74.54%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=455582698.80
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0220
- MODEL_EDGE: AMBER — prob=0.7367, acc=0.4545, auc=0.5660, models=logistic
- OOF_COVERAGE: PASS — coverage=74.54%, gap=20
- BACKTEST_SANITY: AMBER — return=-0.64%, sharpe=-0.420, mdd=1.15%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=98.34, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### SYNTH-A / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.73%, Sharpe=0.701, Sortino=0.795, MDD=0.47%
- Model: prob=81.32%, acc=54.05%, auc=0.455, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=455582698.80
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0220
- MODEL_EDGE: PASS — prob=0.8132, acc=0.5405, auc=0.4553, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=0.73%, sharpe=0.701, mdd=0.47%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=93.19, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### SYNTH-C / Track-S / RED_NOT_RECOMMENDED
- Backtest: return=1.11%, Sharpe=0.580, Sortino=0.410, MDD=0.97%
- Model: prob=16.16%, acc=41.60%, auc=0.540, oof_coverage=74.54%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=537193760.24
- MARKET_REGIME: AMBER — regime_score=40.00, atr_pct=0.0237
- MODEL_EDGE: AMBER — prob=0.1616, acc=0.4160, auc=0.5401, models=logistic
- OOF_COVERAGE: PASS — coverage=74.54%, gap=20
- BACKTEST_SANITY: PASS — return=1.11%, sharpe=0.580, mdd=0.97%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: FAIL — score=46.78, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
