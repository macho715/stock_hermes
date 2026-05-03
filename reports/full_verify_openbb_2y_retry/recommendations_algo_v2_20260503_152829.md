# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-03T11:28:29+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL
Track: BOTH | Period: 2y | Top-N: 1
Data provider: openbb | Synthetic flag: False
Audit log: reports\full_verify_openbb_2y_retry\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | AAPL | S | ELIGIBLE_RECOMMENDATION | 100.00 | 72.06% | 6.09 | 280.14 | 268.93 | 308.15 | 2.50 | 0.75% | 20.00% | 66.93 | 8/9 | data_source=openbb:yfinance; cv_gap=20; 모델 상승확률 72.06%; 단기/중기 추세 확인 |

## Validation details

### AAPL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=1.56%, Sharpe=1.185, Sortino=1.271, MDD=1.24%
- Model: prob=72.06%, acc=47.33%, auc=0.651, oof_coverage=66.08%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=500, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12232704966.48
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0236
- MODEL_EDGE: AMBER — prob=0.7206, acc=0.4733, auc=0.6509, models=logistic
- OOF_COVERAGE: PASS — coverage=66.08%, gap=20
- BACKTEST_SANITY: PASS — return=1.56%, sharpe=1.185, mdd=1.24%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
