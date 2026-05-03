# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-03T11:23:34+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL
Track: BOTH | Period: 3y | Top-N: 1
Data provider: yfinance | Synthetic flag: False
Audit log: reports\full_verify_yfinance\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | AAPL | S | ELIGIBLE_RECOMMENDATION | 87.11 | 49.66% | 2.95 | 280.14 | 268.93 | 308.15 | 2.50 | 0.75% | 20.00% | 66.93 | 7/9 | data_source=yfinance; cv_gap=20; 단기/중기 추세 확인; 백테스트 MDD 2.43% |

## Validation details

### AAPL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.72%, Sharpe=-0.264, Sortino=-0.187, MDD=2.43%
- Model: prob=49.66%, acc=57.78%, auc=0.713, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12232704966.48
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0236
- MODEL_EDGE: AMBER — prob=0.4966, acc=0.5778, auc=0.7133, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=20
- BACKTEST_SANITY: AMBER — return=-0.72%, sharpe=-0.264, mdd=2.43%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=87.11, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
