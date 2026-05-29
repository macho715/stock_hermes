# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-28T22:27:49+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL
Track: BOTH | Period: 3y | Top-N: 1
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_investment_readiness_minimax_advisor_yfinance_20260529_022500\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | AAPL | S | ELIGIBLE_RECOMMENDATION | 75.25 | 94.05% | 9.17 | 312.51 | 300.01 | 343.76 | 2.50 | 0.75% | 20.00% | 60.00 | 9/9 | data_source=yfinance:cache; cv_gap=20; 모델 상승확률 94.05%; 단기/중기 추세 확인 |

## Validation details

### AAPL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.19%, Sharpe=0.114, Sortino=0.127, MDD=1.71%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=94.05%, acc=55.53%, auc=0.613, oof_coverage=100.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=752, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=14671628396.53
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0178
- MODEL_EDGE: PASS — prob=0.9405, acc=0.5553, auc=0.6134, models=logistic
- OOF_COVERAGE: PASS — coverage=100.00%, gap=20
- BACKTEST_SANITY: PASS — return=0.19%, sharpe=0.114, mdd=1.71%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
