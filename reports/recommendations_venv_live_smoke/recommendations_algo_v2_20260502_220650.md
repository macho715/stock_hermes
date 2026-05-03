# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-02T18:06:50+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AMZN, QQQ
Track: BOTH | Period: 3y | Top-N: 2

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | AMZN | S | ELIGIBLE_RECOMMENDATION | 100.00 | 99.24% | 9.89 | 268.26 | 257.53 | 295.09 | 2.50 | 0.75% | 20.00% | 69.89 | 9/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 99.24%; 단기/중기 추세 확인 |
| 2 | QQQ | S | ELIGIBLE_RECOMMENDATION | 100.00 | 98.55% | 9.80 | 674.15 | 647.18 | 741.57 | 2.50 | 0.75% | 20.00% | 27.81 | 8/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 98.55%; 단기/중기 추세 확인 |

## Validation details

### AMZN / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=1.56%, Sharpe=0.710, Sortino=0.604, MDD=2.09%
- Model: prob=99.24%, acc=52.22%, auc=0.630, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12506253745.01
- MARKET_REGIME: PASS — regime_score=85.00, atr_pct=0.0279
- MODEL_EDGE: PASS — prob=0.9924, acc=0.5222, auc=0.6305, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=1.56%, sharpe=0.710, mdd=2.09%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.79%, Sharpe=0.268, Sortino=0.254, MDD=2.58%
- Model: prob=98.55%, acc=42.78%, auc=0.613, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=26333511708.52
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0146
- MODEL_EDGE: AMBER — prob=0.9855, acc=0.4278, auc=0.6130, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=0.79%, sharpe=0.268, mdd=2.58%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
