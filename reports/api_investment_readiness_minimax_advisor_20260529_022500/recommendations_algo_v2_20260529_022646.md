# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-28T22:26:46+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: SYNTH-A
Track: BOTH | Period: 3y | Top-N: 1
Data provider: synthetic | Synthetic flag: True
Audit log: reports\api_investment_readiness_minimax_advisor_20260529_022500\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | SYNTH-A | L | AMBER_WATCHLIST | 74.97 | 88.33% | 16.27 | 122.08 | 107.43 | 146.50 | 1.67 | 0.50% | 12.00% | 34.13 | 9/9 | data_source=synthetic_demo_data; cv_gap=44; 장기 추세 구조 양호; 장기 MDD 한도 내 |

## Validation details

### SYNTH-A / Track-L / AMBER_WATCHLIST
- Backtest: return=1.36%, Sharpe=0.965, Sortino=1.507, MDD=0.56%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=88.33%, acc=64.64%, auc=0.422, oof_coverage=100.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=455582698.80
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0220
- MODEL_EDGE: PASS — prob=0.8833, acc=0.6464, auc=0.4217, models=logistic
- OOF_COVERAGE: PASS — coverage=100.00%, gap=44
- BACKTEST_SANITY: PASS — return=1.36%, sharpe=0.965, mdd=0.56%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=93.17, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
