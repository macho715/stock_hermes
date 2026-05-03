# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-02T16:19:39+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: SYNTH-A
Track: L | Period: 5y | Top-N: 1

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | SYNTH-A | L | ACCUMULATE_RECOMMENDATION | 85.05 | 56.19% | 5.98 | 79.37 | 69.85 | 95.25 | 1.67 | 0.50% | 12.00% | 52.49 | 9/9 | data_source=synthetic_demo_data; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |

## Validation details

### SYNTH-A / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=0.15%, Sharpe=0.245, Sortino=0.154, MDD=0.24%
- Model: prob=56.19%, acc=58.86%, auc=0.614, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=315129826.77
- MARKET_REGIME: PASS — regime_score=65.00, atr_pct=0.0218
- MODEL_EDGE: PASS — prob=0.5619, acc=0.5886, auc=0.6140, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=0.15%, sharpe=0.245, mdd=0.24%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=85.05, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
