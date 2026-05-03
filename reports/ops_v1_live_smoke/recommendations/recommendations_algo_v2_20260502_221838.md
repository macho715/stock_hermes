# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-02T18:18:38+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AMZN, QQQ
Track: BOTH | Period: 3y | Top-N: 2

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | QQQ | S | ELIGIBLE_RECOMMENDATION | 100.00 | 96.46% | 9.50 | 674.15 | 647.18 | 741.57 | 2.50 | 0.75% | 20.00% | 27.81 | 8/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 96.46%; 단기/중기 추세 확인 |
| 2 | AMZN | S | ELIGIBLE_RECOMMENDATION | 95.72 | 98.17% | 9.74 | 268.26 | 257.53 | 295.09 | 2.50 | 0.75% | 20.00% | 69.89 | 8/9 | data_source=yfinance; cv_gap=5; 모델 상승확률 98.17%; 단기/중기 추세 확인 |

## Validation details

### QQQ / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.63%, Sharpe=0.207, Sortino=0.198, MDD=2.64%
- Model: prob=96.46%, acc=45.00%, auc=0.600, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=26333511708.52
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0146
- MODEL_EDGE: AMBER — prob=0.9646, acc=0.4500, auc=0.6001, models=xgb-cuda
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: PASS — return=0.63%, sharpe=0.207, mdd=2.64%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AMZN / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.73%, Sharpe=-0.379, Sortino=-0.348, MDD=2.37%
- Model: prob=98.17%, acc=56.39%, auc=0.558, oof_coverage=75.00%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=753, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12506253745.01
- MARKET_REGIME: PASS — regime_score=85.00, atr_pct=0.0279
- MODEL_EDGE: PASS — prob=0.9817, acc=0.5639, auc=0.5581, models=xgb-cuda
- OOF_COVERAGE: PASS — coverage=75.00%, gap=5
- BACKTEST_SANITY: AMBER — return=-0.73%, sharpe=-0.379, mdd=2.37%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=95.72, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
