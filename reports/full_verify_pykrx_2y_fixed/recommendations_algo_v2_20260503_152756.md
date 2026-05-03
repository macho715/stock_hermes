# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-03T11:27:56+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: 005930.KS
Track: BOTH | Period: 2y | Top-N: 1
Data provider: pykrx | Synthetic flag: False
Audit log: reports\full_verify_pykrx_2y_fixed\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 005930.KS | S | ELIGIBLE_RECOMMENDATION | 100.00 | 100.00% | 10.00 | 220500.00 | 209475.00 | 242550.00 | 2.00 | 0.75% | 20.00% | 0.07 | 9/9 | data_source=pykrx; cv_gap=20; 모델 상승확률 100.00%; 단기/중기 추세 확인 |

## Validation details

### 005930.KS / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=5.02%, Sharpe=1.484, Sortino=1.185, MDD=2.64%
- Model: prob=100.00%, acc=50.00%, auc=0.745, oof_coverage=66.35%
- Risk plan: stop=5.00%, tp2=10.00%, R/R=2.00, position_value=15000.00
- DATA_ROWS: PASS — rows=484, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=4882969073035.00
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0407
- MODEL_EDGE: PASS — prob=1.0000, acc=0.5000, auc=0.7450, models=logistic
- OOF_COVERAGE: PASS — coverage=66.35%, gap=20
- BACKTEST_SANITY: PASS — return=5.02%, sharpe=1.484, mdd=2.64%
- RISK_PLAN: PASS — stop_pct=5.00%, tp2_pct=10.00%, rr=2.00, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
