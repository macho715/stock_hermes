# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-08T20:51:24+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA
Track: BOTH | Period: 3y | Top-N: 3
Data provider: auto | Synthetic flag: True
Audit log: reports/recommendations/audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | MSFT | S | AMBER_REVIEW_ONLY | 67.28 | 60.24% | 4.43 | 98.91 | 94.95 | 108.80 | 2.50 | 0.75% | 20.00% | 189.56 | 6/9 | data_source=synthetic_demo_data; cv_gap=20; 모델 상승확률 60.24%; 백테스트 MDD 2.80% |
| 2 | NVDA | S | RED_NOT_RECOMMENDED | 52.09 | 0.42% | -3.94 | 113.84 | 109.29 | 125.23 | 2.50 | 0.75% | 20.00% | 164.70 | 6/9 | data_source=synthetic_demo_data; cv_gap=20; 백테스트 MDD 1.86%; R/R 2.50 통과 |
| 3 | MSFT | L | RED_NOT_RECOMMENDED | 48.29 | 40.81% | 1.06 | 98.91 | 87.04 | 118.69 | 1.67 | 0.50% | 12.00% | 42.13 | 6/9 | data_source=synthetic_demo_data; cv_gap=63; 장기 MDD 한도 내; Track-L 기준 미달 |

## Validation details

### MSFT / Track-S / AMBER_REVIEW_ONLY
- Backtest: return=0.83%, Sharpe=0.378, Sortino=0.380, MDD=2.80%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=60.24%, acc=44.90%, auc=0.595, oof_coverage=74.54%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=432557518.03
- MARKET_REGIME: AMBER — regime_score=30.00, atr_pct=0.0241
- MODEL_EDGE: AMBER — prob=0.6024, acc=0.4490, auc=0.5947, models=logistic
- OOF_COVERAGE: PASS — coverage=74.54%, gap=20
- BACKTEST_SANITY: PASS — return=0.83%, sharpe=0.378, mdd=2.80%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: AMBER — score=67.28, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### NVDA / Track-S / RED_NOT_RECOMMENDED
- Backtest: return=0.31%, Sharpe=0.156, Sortino=0.148, MDD=1.86%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=0.42%, acc=66.39%, auc=0.712, oof_coverage=74.54%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=480685578.18
- MARKET_REGIME: AMBER — regime_score=25.00, atr_pct=0.0251
- MODEL_EDGE: AMBER — prob=0.0042, acc=0.6639, auc=0.7122, models=logistic
- OOF_COVERAGE: PASS — coverage=74.54%, gap=20
- BACKTEST_SANITY: PASS — return=0.31%, sharpe=0.156, mdd=1.86%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: FAIL — score=52.09, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### MSFT / Track-L / RED_NOT_RECOMMENDED
- Backtest: return=0.17%, Sharpe=0.476, Sortino=0.175, MDD=0.20%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=40.81%, acc=54.05%, auc=0.721, oof_coverage=75.00%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=760, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=432557518.03
- MARKET_REGIME: AMBER — regime_score=30.00, atr_pct=0.0241
- MODEL_EDGE: AMBER — prob=0.4081, acc=0.5405, auc=0.7207, models=logistic
- OOF_COVERAGE: PASS — coverage=75.00%, gap=63
- BACKTEST_SANITY: PASS — return=0.17%, sharpe=0.476, mdd=0.20%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: FAIL — score=48.29, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
