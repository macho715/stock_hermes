# Stock Recommendation Report — Algorithm v2

Generated: 2026-05-06T03:08:53+00:00

Boundary: `screening_output_only`; manual approval required; no broker order execution; not financial advice.

Algorithm: leak-safe purged walk-forward CV, out-of-fold backtest signals, ATR-adjusted stop/target, fixed-risk position sizing.

Universe: AAPL, MSFT, NVDA, TSLA, AMZN, GOOGL, META, SPY, QQQ
Track: BOTH | Period: 3y | Top-N: 5
Data provider: yfinance | Synthetic flag: False
Audit log: reports\api_recommend_us\audit_log.jsonl

| Rank | Ticker | Track | Verdict | Score | Prob | EV% | Entry | Stop | TP2 | R/R | Risk% | MaxPos% | Qty | Confirms | Evidence |
|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | NVDA | L | ACCUMULATE_RECOMMENDATION | 100.00 | 82.39% | 14.37 | 196.50 | 172.92 | 235.80 | 1.67 | 0.50% | 12.00% | 21.20 | 8/9 | data_source=yfinance; cv_gap=63; 장기 추세 구조 양호; 52주 고점 대비 과열이 아닌 조정권 |
| 2 | QQQ | S | ELIGIBLE_RECOMMENDATION | 100.00 | 99.55% | 9.94 | 681.61 | 654.35 | 749.77 | 2.50 | 0.75% | 20.00% | 27.51 | 7/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 99.55%; 단기/중기 추세 확인 |
| 3 | SPY | S | ELIGIBLE_RECOMMENDATION | 100.00 | 99.52% | 9.93 | 723.77 | 694.82 | 796.15 | 2.50 | 0.75% | 20.00% | 25.91 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 99.52%; 단기/중기 추세 확인 |
| 4 | GOOGL | S | ELIGIBLE_RECOMMENDATION | 100.00 | 79.89% | 7.18 | 388.43 | 372.89 | 427.27 | 2.50 | 0.75% | 20.00% | 48.27 | 9/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 79.89%; 단기/중기 추세 확인 |
| 5 | AAPL | S | ELIGIBLE_RECOMMENDATION | 95.86 | 64.84% | 5.08 | 284.18 | 272.81 | 312.60 | 2.50 | 0.75% | 20.00% | 65.98 | 8/9 | data_source=yfinance; cv_gap=20; 모델 상승확률 64.84%; 단기/중기 추세 확인 |

## Validation details

### NVDA / Track-L / ACCUMULATE_RECOMMENDATION
- Backtest: return=-0.60%, Sharpe=-0.244, Sortino=-0.177, MDD=2.37%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=82.39%, acc=39.20%, auc=0.737, oof_coverage=74.48%
- Risk plan: stop=12.00%, tp2=20.00%, R/R=1.67, position_value=4166.67
- DATA_ROWS: PASS — rows=751, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=29395471120.58
- MARKET_REGIME: PASS — regime_score=80.00, atr_pct=0.0314
- MODEL_EDGE: AMBER — prob=0.8239, acc=0.3920, auc=0.7372, models=logistic
- OOF_COVERAGE: PASS — coverage=74.48%, gap=63
- BACKTEST_SANITY: PASS — return=-0.60%, sharpe=-0.244, mdd=2.37%
- RISK_PLAN: PASS — stop_pct=12.00%, tp2_pct=20.00%, rr=1.67, risk_budget=0.50%
- TRACK_SCORE: PASS — score=100.00, green_threshold=80.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### QQQ / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-0.63%, Sharpe=-0.280, Sortino=-0.211, MDD=2.48%
- Backtest honesty: AMBER (pass=3, amber=2, fail=0)
- Model: prob=99.55%, acc=41.18%, auc=0.614, oof_coverage=74.69%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=751, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=26197271972.51
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0142
- MODEL_EDGE: AMBER — prob=0.9955, acc=0.4118, auc=0.6142, models=logistic
- OOF_COVERAGE: PASS — coverage=74.69%, gap=20
- BACKTEST_SANITY: AMBER — return=-0.63%, sharpe=-0.280, mdd=2.48%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### SPY / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=0.02%, Sharpe=0.014, Sortino=0.012, MDD=2.11%
- Backtest honesty: AMBER (pass=4, amber=1, fail=0)
- Model: prob=99.52%, acc=35.85%, auc=0.625, oof_coverage=74.69%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=751, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=36831245453.50
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0106
- MODEL_EDGE: AMBER — prob=0.9952, acc=0.3585, auc=0.6246, models=logistic
- OOF_COVERAGE: PASS — coverage=74.69%, gap=20
- BACKTEST_SANITY: PASS — return=0.02%, sharpe=0.014, mdd=2.11%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### GOOGL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=2.69%, Sharpe=1.128, Sortino=0.706, MDD=0.84%
- Backtest honesty: PASS (pass=5, amber=0, fail=0)
- Model: prob=79.89%, acc=54.62%, auc=0.740, oof_coverage=74.69%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=751, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=9529693355.28
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0253
- MODEL_EDGE: PASS — prob=0.7989, acc=0.5462, auc=0.7397, models=logistic
- OOF_COVERAGE: PASS — coverage=74.69%, gap=20
- BACKTEST_SANITY: PASS — return=2.69%, sharpe=1.128, mdd=0.84%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=100.00, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False

### AAPL / Track-S / ELIGIBLE_RECOMMENDATION
- Backtest: return=-1.36%, Sharpe=-0.478, Sortino=-0.304, MDD=3.33%
- Backtest honesty: AMBER (pass=3, amber=2, fail=0)
- Model: prob=64.84%, acc=57.14%, auc=0.717, oof_coverage=74.69%
- Risk plan: stop=4.00%, tp2=10.00%, R/R=2.50, position_value=18750.00
- DATA_ROWS: PASS — rows=751, min_rows=260
- LIQUIDITY: PASS — avg_dollar_volume_20d=12380671500.59
- MARKET_REGIME: PASS — regime_score=100.00, atr_pct=0.0234
- MODEL_EDGE: PASS — prob=0.6484, acc=0.5714, auc=0.7171, models=logistic
- OOF_COVERAGE: PASS — coverage=74.69%, gap=20
- BACKTEST_SANITY: AMBER — return=-1.36%, sharpe=-0.478, mdd=3.33%
- RISK_PLAN: PASS — stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%
- TRACK_SCORE: PASS — score=95.86, green_threshold=75.00
- AUTOMATION_BOUNDARY: PASS — screening_output_only; broker_order_execution=False
