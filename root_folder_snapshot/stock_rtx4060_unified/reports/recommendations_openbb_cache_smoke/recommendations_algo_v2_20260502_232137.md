# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-02T19:21:37+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL
Track: BOTH | Period: 3y | Top-N: 1
Data provider: openbb | Synthetic flag: False
Audit log: reports\recommendations_openbb_cache_smoke\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | AAPL | S | ELIGIBLE_RECOMMENDATION | 87.65 | 46.25% | 2.48 | 280.14 | 268.93 | 308.15 | 2.50 | 0.75% | 20.00% | 66.93 | 8/9 | data_source=openbb:yfinance; cv_gap=20; 단기/중기 추세 확인; 백테스트 MDD 2.03% |

## Validation details

### AAPL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.33%, Sharpe=-0.149, Sortino=-0.117, MDD=2.03%
- Model: prob=46.25%, acc=58.54%, auc=0.713, oof_coverage=74.53%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12232704966.48
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0236
- MODEL_EDGE: AMBER — prob=0.4625, acc=0.5854, auc=0.7128, models=logistic
- OOF_COVERAGE: PASS — coverage=74.53%, gap=20
- BACKTEST_SANITY: PASS — return=-0.33%, sharpe=-0.149, mdd=2.03%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=87.65, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
