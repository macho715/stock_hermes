# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-02T16:19:55+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: SYNTH-A
Track: S | Period: 5y | Top-N: 1

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | SYNTH-A | S | RED_NOT_RECOMMENDED | 63.54 | 1.30% | -3.82 | 79.37 | 76.20 | 87.31 | 2.50 | 0.75% | 20.00% | 236.22 | 7/9 | data_source=synthetic_demo_data; cv_gap=20; 백테스트 MDD 0.76%; R/R 2.50 통과 |

## Validation details

### SYNTH-A / Track-S / RED_NOT_RECOMMENDED
- Backtest: return=0.32%, Sharpe=0.285, Sortino=0.186, MDD=0.76%
- Model: prob=1.30%, acc=55.92%, auc=0.591, oof_coverage=74.54%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=315129826.77
- MARKET_REGIME: PASS — regime_score=65.00, atr_pct=0.0218
- MODEL_EDGE: AMBER — prob=0.0130, acc=0.5592, auc=0.5905, models=logistic
- OOF_COVERAGE: PASS — coverage=74.54%, gap=20
- BACKTEST_SANITY: PASS — return=0.32%, sharpe=0.285, mdd=0.76%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: FAIL — score=63.54, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
