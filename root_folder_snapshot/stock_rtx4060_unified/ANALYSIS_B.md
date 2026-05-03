# ANALYSIS_B — stock_rtx4060_unified Deep Reader

**Analyst**: Agent R-B
**Date**: 2026-05-03
**Project**: `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified`
**Purpose**: Document project purpose, architecture, and key modules.

---

## 1. Project Purpose

`stock_rtx4060_unified` is a **local stock-candidate recommendation engine** for two-track screening:

- **Track-S** (short-term tactical): Green requires score >= 75.00 + all validation gates.
- **Track-L** (long-term accumulation): Green requires score >= 80.00 + all validation gates.

It produces ranked recommendation reports (`ELIGIBLE_RECOMMENDATION`, `ACCUMULATE_RECOMMENDATION`, `AMBER_*`, `RED_*`, `ZERO_*`) with auditable evidence. Output is `screening_output_only` — not broker order execution, not financial advice.

**Core constraint**: Never let model probability alone produce a Green verdict.

---

## 2. Core Modules

### recommendation_engine.py

**Class**: `RecommendationEngine`
**Key method**: `run()` — evaluates universe tickers across Track-S and/or Track-L, sorts by verdict priority then score, returns top-N `RecommendationResult` list.

**Config dataclass**: `RecommendationConfig`
Fields include: `universe`, `track`, `period`, `horizon_s` (20), `horizon_l` (63), `top_n`, `synthetic`, `min_rows` (260), `short_green_score` (75.0), `long_green_score` (80.0), `stop_loss_pct_s` (-4%), `take_profit_2_pct_s` (+10%), `risk_per_trade_pct_s` (0.75%), `max_position_pct_s` (20%), `risk_per_trade_pct_l` (0.50%), `max_position_pct_l` (12%), `min_risk_reward` (2.0), `model_kind`, `xgb_device`, `cv_gap`, `data_provider`, etc.

**Verdict types**: ELIGIBLE_RECOMMENDATION, ACCUMULATE_RECOMMENDATION, AMBER_REVIEW_ONLY, AMBER_WATCHLIST, RED_NOT_RECOMMENDED, RED_DATA_INSUFFICIENT, RED_DATA_OR_MODEL_ERROR, ZERO_RISK_PLAN_FAILED

**Key internal functions**:
- `parse_universe(value)` — comma/space separated string → list of ticker strings
- `load_ohlcv()` — delegates to `load_ohlcv_with_provider()` for auto/synthetic/yfinance/openbb
- `_market_snapshot(df)` — computes SMA20/50/200, ATR, avg dollar volume, return/drawdown stats, regime score
- `_risk_plan(track, snap, cfg, capital)` — ATR-adjusted entry/stop/TP1/TP2, fixed-risk quantity sizing
- `_score_track_s()` / `_score_track_l()` — scoring: model edge, trend, liquidity, breakout, volatility, backtest quality, R/R
- `_validation_checks()` — DATA_ROWS, LIQUIDITY, MARKET_REGIME, MODEL_EDGE, OOF_COVERAGE, BACKTEST_SANITY, RISK_PLAN, TRACK_SCORE, AUTOMATION_BOUNDARY
- `_verdict()` — derives Verdict from checks + score thresholds
- `render_markdown(results, cfg)` — markdown report string

**RecommendationResult dataclass fields**: ticker, track, verdict, recommendation_rank_score, candidate_label, screening_output_only, latest_close, entry, stop, tp1, tp2, stop_pct, tp2_pct, risk_reward, risk_budget_pct, max_position_pct, suggested_quantity, suggested_position_value, direction_prob, expected_value_pct, model_accuracy, model_auc, oof_coverage, backtest_return_pct, backtest_sharpe, backtest_sortino, backtest_mdd_pct, profit_factor, avg_dollar_volume_20d, volume_ratio_20d, market_regime_score, return_20d_pct, return_60d_pct, drawdown_252d_pct, confirmations_passed, confirmations_total, validations (list of ValidationCheck), reasons, generated_at_utc.

---

### feature_engine.py

**Class**: `TechnicalIndicators`
**Method**: `build_all(horizon)` — adds 20+ technical features (SMA, EMA, RSI, MACD, Bollinger, ATR, volume ratios, etc.) to OHLCV DataFrame, returns feature DataFrame with `target_direction` column (1 if price up in N days, 0 otherwise).

**Key function**: `feature_columns(df)` — returns list of feature column names for model input.

---

### ensemble_model.py

**Class**: `DirectionModel`
**Method**: `fit(X, y)` — trains XGBoost or LogisticRegression depending on `model_kind`; `predict_proba(X)` returns probability of upward direction.

**Key function**: `_safe_auc(y, prob)` — computes AUC safely, returns 0.5 on error.

**ModelConfig dataclass**: holds horizon, n_splits, gap, model_kind, xgb_device, use_lstm, xgb_params.

---

### backtester.py

**Class**: `Backtester`
**Method**: `run(prices, signals)` — walk-forward backtest using out-of-fold probabilities as signals; computes total_return_pct, sharpe_ratio, sortino_ratio, max_drawdown_pct, profit_factor.

**BacktestConfig dataclass**: initial_capital, threshold_buy, threshold_sell, stop_loss_pct, take_profit_pct, risk_per_trade_pct, max_position_pct, max_monthly_loss_pct.

---

### dashboard_bridge.py

**Function**: `write_dashboard_snapshot(recommendation_json, output)` — reads recommendation JSON from `RecommendationEngine.write_reports()`, produces `dashboard_snapshot.v1` JSON.

**Schema**: top-level fields — schema_version, generated_at_utc, source, source_recommendation_json, mode (report_only), disclaimer, audit_log_path, algorithm_patch, config (universe, track, period, top_n, synthetic, data_provider, model_kind, xgb_device, cv_gap), result_count, results.

**Per-result fields**: rank, ticker, track, verdict, candidate_label, score, probability, expected_value_pct, entry, latest_close, stop, tp1, tp2, stop_pct, tp2_pct, risk_reward, risk_budget_pct, max_position_pct, suggested_quantity, suggested_position_value, model_accuracy, model_auc, oof_coverage, backtest_return_pct, backtest_sharpe, backtest_sortino, backtest_mdd_pct, profit_factor, confirmations_passed, confirmations_total, screening_output_only (must be true), validations, reasons, generated_at_utc.

**Validation**: required fields enforced, screening_output_only=True enforced, no broker/order fields introduced.

---

## 3. API Server (Flask)

**Not present.** This project uses a file-based report bridge, not an HTTP server.

- CLI command `dashboard-export` converts recommendation JSON → dashboard_snapshot.json
- No mandatory server, no port, no MCP server required
- Dashboard (`stock_pred_v5.jsx`) imports snapshot via browser file import button

---

## 4. Track-S and Track-L Screening

**Track-S** (short-term, horizon=20):
- Green threshold: score >= 75.00
- Amber threshold: score >= 65.00
- Default stop: -4.00%, TP1: +5.00%, TP2: +10.00%
- Risk budget: 0.75% per trade, max position 20%

**Track-L** (long-term, horizon=63):
- Green threshold: score >= 80.00
- Amber threshold: score >= 70.00
- Default stop: -12.00%, wider TP review
- Risk budget: 0.50% per trade, max position 12%

Both tracks pass through the same 9 gate checks; Track-S has tighter MDD limits (25% vs 35%).

---

## 5. Risk Gate Validation

Every candidate passes through all of:

| Gate | Track-S | Track-L | Fail verdict |
|---|---|---|---|
| DATA_ROWS | rows >= 260 | same | RED_DATA_INSUFFICIENT |
| LIQUIDITY | avg_dollar_vol >= $10M | same | AMBER |
| MARKET_REGIME | regime_score >= 45 | regime_score >= 40 | AMBER |
| MODEL_EDGE | prob >= 0.56, acc >= 0.50 | prob >= 0.53, acc >= 0.50 | AMBER |
| OOF_COVERAGE | coverage >= 45% | same | AMBER |
| BACKTEST_SANITY | mdd <= 25%, sharpe >= -0.25 | mdd <= 35% | AMBER |
| RISK_PLAN | stop < entry, rr >= 2.0, budget > 0 | stop < entry, rr >= 1.5 | ZERO_RISK_PLAN_FAILED |
| TRACK_SCORE | score >= 75 | score >= 80 | RED_NOT_RECOMMENDED |
| AUTOMATION_BOUNDARY | always PASS | same | screening_output_only flag |

ZERO verdict blocks all execution. Model probability alone cannot produce a Green verdict — score and checks must both pass.

---

## 6. Tech Stack

| Layer | Technology |
|---|---|---|
| Language | Python 3.11+, verified 3.12 |
| ML primary | XGBoost (CPU/GPU via hist/cuda tree method, version-aware) |
| ML fallback | scikit-learn LogisticRegression with StandardScaler + median imputation |
| CV | sklearn TimeSeriesSplit with configurable gap = horizon |
| Data | pandas, numpy |
| Data fetch | yfinance (>= 0.2.66), openbb (optional) |
| CLI | argparse subcommands via root main.py + src/stock_rtx4060/main.py |
| Windows runner | PowerShell run.ps1 selecting .venv\Scripts\python.exe |
| Reports | JSON + Markdown output |
| Dashboard bridge | file-based JSON export for JSX dashboard import |
| Testing | pytest |
| Audit | JSONL via audit_log.py with secret masking |
| Continue | PR-quality gate checks under .continue/checks/ |

---

## 7. dashboard_snapshot.v1 JSON Schema

```json
{
  "schema_version": "dashboard_snapshot.v1",
  "generated_at_utc": "2026-05-03T00:00:00Z",
  "source": "stock_rtx4060_unified",
  "source_recommendation_json": "reports/.../recommendations_algo_v2_20260503_000000.json",
  "mode": "report_only",
  "disclaimer": "screening_output_only; manual approval required; no broker order execution; not financial advice",
  "audit_log_path": "reports/.../audit_log.jsonl",
  "algorithm_patch": "v2 leak-safe CV + ATR risk plan + fixed-risk sizing + OOF backtest",
  "config": {
    "universe": ["AAPL", "NVDA", "..."],
    "track": "BOTH",
    "period": "3y",
    "top_n": 5,
    "synthetic": false,
    "data_provider": "auto",
    "model_kind": "logistic",
    "xgb_device": "cpu",
    "cv_gap": null
  },
  "result_count": 5,
  "results": [
    {
      "rank": 1,
      "ticker": "NVDA",
      "track": "S",
      "verdict": "ELIGIBLE_RECOMMENDATION",
      "candidate_label": "Track-S 추천 후보: 수동 승인 필요",
      "score": 82.30,
      "probability": 0.6200,
      "expected_value_pct": 3.80,
      "entry": 875.50,
      "latest_close": 875.50,
      "stop": 840.48,
      "tp1": 919.28,
      "tp2": 963.05,
      "stop_pct": 0.0400,
      "tp2_pct": 0.1000,
      "risk_reward": 2.50,
      "risk_budget_pct": 0.0075,
      "max_position_pct": 0.2000,
      "suggested_quantity": 89.29,
      "suggested_position_value": 78194.20,
      "model_accuracy": 0.5400,
      "model_auc": 0.5800,
      "oof_coverage": 0.5200,
      "backtest_return_pct": 8.50,
      "backtest_sharpe": 0.350,
      "backtest_sortino": 0.480,
      "backtest_mdd_pct": 12.30,
      "profit_factor": 1.82,
      "confirmations_passed": 7,
      "confirmations_total": 9,
      "screening_output_only": true,
      "validations": [
        {"name": "DATA_ROWS", "status": "PASS", "evidence": "rows=760, min_rows=260"},
        {"name": "LIQUIDITY", "status": "PASS", "evidence": "avg_dollar_volume_20d=..."},
        {"name": "MARKET_REGIME", "status": "PASS", "evidence": "regime_score=80.00, atr_pct=0.0300"},
        {"name": "MODEL_EDGE", "status": "PASS", "evidence": "prob=0.6200, acc=0.5400, auc=0.5800, models=xgb"},
        {"name": "OOF_COVERAGE", "status": "PASS", "evidence": "coverage=52.00%, gap=20"},
        {"name": "BACKTEST_SANITY", "status": "PASS", "evidence": "return=8.50%, sharpe=0.350, mdd=12.30%"},
        {"name": "RISK_PLAN", "status": "PASS", "evidence": "stop_pct=4.00%, tp2_pct=10.00%, rr=2.50, risk_budget=0.75%"},
        {"name": "TRACK_SCORE", "status": "PASS", "evidence": "score=82.30, green_threshold=75.00"},
        {"name": "AUTOMATION_BOUNDARY", "status": "PASS", "evidence": "screening_output_only; broker_order_execution=False"}
      ],
      "reasons": ["data_source=yfinance", "cv_gap=20", "모델 상승확률 0.62", "단기/중기 추세 확인", "20일 고점권/돌파 후보", "R/R 2.50 통과", "..."],
      "generated_at_utc": "2026-05-03T00:00:00Z"
    }
  ]
}
```

---

## 8. Key File Paths

| File | Purpose |
|---|---|
| `src/stock_rtx4060/recommendation_engine.py` | Core recommendation engine: RecommendationEngine, RecommendationConfig, RecommendationResult, parse_universe |
| `src/stock_rtx4060/feature_engine.py` | TechnicalIndicators, feature_columns |
| `src/stock_rtx4060/ensemble_model.py` | DirectionModel, ModelConfig, EnsemblePredictor, xgb_params_for_device |
| `src/stock_rtx4060/backtester.py` | Backtester, BacktestConfig, Trade, BacktestResult |
| `src/stock_rtx4060/dashboard_bridge.py` | write_dashboard_snapshot, build_dashboard_snapshot, RESULT_REQUIRED_FIELDS |
| `src/stock_rtx4060/hw_profile.py` | GPU/RTX 4060 detection, RuntimeStatus |
| `src/stock_rtx4060/risk_rules.py` | Gate enum, RiskConfig, evaluate_track_s_candidate |
| `src/stock_rtx4060/reports.py` | ReportWriter for daily brief/risk dashboard |
| `src/stock_rtx4060/data_providers.py` | Provider router: auto/synthetic/yfinance/openbb |
| `src/stock_rtx4060/audit_log.py` | JSONL audit events with secret masking |
| `src/stock_rtx4060/ops_workflow.py` | ops-v1 pipeline + approval artifacts |
| `main.py` (root) | CLI entrypoint wrapper |
| `src/stock_rtx4060/main.py` | Package CLI subcommands |
| `run.ps1` | Windows operator runner |
| `dashboard/stock_pred_v5.jsx` | Repo-owned dashboard copy |
| `dashboard/bridge_smoke.html` | Browser smoke test harness |
| `dashboard/verify_bridge_smoke.mjs` | Node verification script |
| `requirements.txt` | Core: numpy, pandas, scikit-learn, yfinance, xgboost, flask, flask-cors |
| `docs/SPEC_DASHBOARD_BRIDGE_2026-05-03.md` | Dashboard bridge specification |
| `docs/AGENTS.md` | Project instructions |
| `.continue/checks/` | 8 PR-quality gate checks |
| `tests/` | pytest regression tests (19 verified passing) |

## 1. Project Purpose

`stock_rtx4060_unified` is a consolidated, report-only CLI toolkit for stock-candidate screening and walk-forward backtesting. It produces ranked Markdown/JSON recommendation reports for manual human review. The system supports two screening tracks: **Track-S** (short-term tactical, horizon=20 bars) and **Track-L** (long-term accumulation, horizon=63 bars). It never submits broker orders, never provides guaranteed-return claims, and marks all outputs `screening_output_only`. The target runtime is Windows 11 with an NVIDIA RTX 4060 Laptop GPU (8 GB VRAM) via WSL2/CUDA.

---

## 2. Core Modules and Responsibilities

| Module | File | Responsibility |
|---|---|---|
| CLI entry | `src/stock_rtx4060/main.py` | Subcommand parser: `env`, `benchmark`, `report`, `predict`, `recommend`, `ops-v1`, `dashboard-export`, `demo`, `journal`, `self-test` |
| Root wrapper | `main.py` (root) | Prepends `src/` to `sys.path`, dispatches to package CLI |
| Windows runner | `run.ps1` | Selects `.venv\Scripts\python.exe`, runs CLI commands |
| Recommendation | `src/stock_rtx4060/recommendation_engine.py` | Orchestrates: OHLCV load, feature build, walk-forward CV, backtest, risk gate, ranking, report write (markdown + JSON) |
| Feature engineering | `src/stock_rtx4060/feature_engine.py` | Normalizes OHLCV columns; builds 60+ technical indicators via `TechnicalIndicators` class; `feature_lag=1` shift prevents same-bar label leakage |
| Ensemble model | `src/stock_rtx4060/ensemble_model.py` | `DirectionModel` (XGBoost or logistic fallback) wrapped in `EnsemblePredictor` with walk-forward `TimeSeriesSplit(gap=horizon)` |
| Backtester | `src/stock_rtx4060/backtester.py` | Dry-run trade simulation: transaction cost, slippage, stop loss, take profit, monthly loss stop, fractional Kelly sizing |
| Risk rules | `src/stock_rtx4060/risk_rules.py` | `Gate` enum (GREEN/AMBER/RED/ZERO); `RiskConfig` capital allocation; `evaluate_track_s_candidate` / `evaluate_track_l_candidate` position sizing |
| Reports writer | `src/stock_rtx4060/reports.py` | `ReportWriter` class: `daily_brief`, `risk_dashboard`, `track_l_thesis`, `monthly_scorecard`, `journal_append` |
| Benchmark | `src/stock_rtx4060/benchmark.py` | Synthetic OHLCV benchmark harness: feature build timing, CPU/XGBoost/LSTM training comparison |
| Hardware profile | `src/stock_rtx4060/hw_profile.py` | Subprocess-based `nvidia-smi` and TensorFlow GPU probe; `RuntimeStatus` dataclass; `OMP_NUM_THREADS` / `MKL_NUM_THREADS` environment setup |
| Data providers | `src/stock_rtx4060/data_providers.py` | Provider router: `auto`, `synthetic`, `yfinance`, `openbb`; OHLCV cache per CLI run; JSONL audit logging |
| Ops workflow | `src/stock_rtx4060/ops_workflow.py` | Full pipeline + manual approval artifacts: recommendations + daily brief + `approval_journal_template.csv` + ZERO log + summary JSON |
| Dashboard bridge | `src/stock_rtx4060/dashboard_bridge.py` | Converts recommendation JSON to `dashboard_snapshot.v1` for `stock_pred_v5.jsx` import |
| Audit log | `src/stock_rtx4060/audit_log.py` | JSONL audit events; `mask_secret` for API keys, tokens, passwords, account IDs, private URLs |
| MCP adapter | `src/stock_rtx4060/mcp_adapter.py` | Phase 1 read/report-only adapter contract; no local MCP server, no broker/account/destructive filesystem capabilities |

---

## 3. Model / Algorithm Description

### Walk-Forward Ensemble

The core algorithm is a **walk-forward ensemble** with the following properties:

1. **OHLCV normalization** — any CSV/yfinance/OpenBB OHLCV variant is normalized to flat `Open/High/Low/Close/Volume` columns.
2. **Feature engineering** — `TechnicalIndicators` builds 60+ features: returns, moving averages (5/10/20/50/200), RSI, MACD, Bollinger Bands, ATR, volume ratios, etc. `feature_lag=1` shifts features so the model never sees the bar it is predicting from.
3. **Targets** — `target_direction` (1 if forward-return > 0), `target_return` (raw forward return). Horizon is configurable (default 5 bars for generic, 20 for Track-S, 63 for Track-L).
4. **Walk-forward CV** — `TimeSeriesSplit(gap=horizon)` ensures the model never trains on future data relative to the prediction horizon. Out-of-fold (OOF) probabilities are collected for leak-safe backtesting.
5. **Model path** — `EnsemblePredictor` uses `DirectionModel` which first tries XGBoost on the configured device (CPU or CUDA), then falls back to CPU XGBoost, then falls back to scikit-learn `LogisticRegression` with median imputation + standard scaling. `model_kind` can be `auto`, `xgb`, or `logistic`.
6. **XGBoost version awareness** — `xgb_params_for_device()` maps device string `"cuda"` to `"hist"`+`"cuda"` for XGBoost 2.x+ and `"gpu_hist"` for pre-2.0.
7. **OOF probabilities** — stored after each fold, used for backtest sanity check and AUC/accuracy reporting.
8. **Prediction** — fresh probabilities collected via the same walk-forward split on the full dataset.

### Risk Gate Pipeline

1. **DATA_ROWS** — must have >= 260 rows (1 year of trading days).
2. **LIQUIDITY** — average dollar volume >= $5M (configurable).
3. **MARKET_REGIME** — trend detection (SMA 50 vs SMA 200 cross).
4. **MODEL_EDGE** — OOF AUC > 0.52 and accuracy > 0.50.
5. **OOF_COVERAGE** — at least 80% of train folds produced valid predictions.
6. **BACKTEST_SANITY** — annualized return > 0 and Sharpe > 0.
7. **RISK_PLAN** — entry > 0, stop > 0, stop < entry, risk budget > 0, Risk/Reward >= track threshold.
8. **TRACK_SCORE** — Track-S score >= 75 for GREEN, >= 65 for AMBER. Track-L score >= 80 for GREEN, >= 70 for AMBER.
9. **AUTOMATION_BOUNDARY** — AUTO_BUY, BROKER_ORDER, MARGIN_OPTIONS, NO_STOP, INSIDE_INFO, GUARANTEED_RETURN → ZERO verdict.

### Backtester

`Backtester` simulates dry-run trades using:
- Entry: model probability > `threshold_buy` (default 0.56)
- Exit: probability < `threshold_sell` (0.45), stop-loss hit, or take-profit hit
- Costs: `transaction_cost` 0.1%, `slippage` 0.05%
- Position sizing: Kelly fraction (default 0.25) × risk_per_trade_pct (0.75%) of track capital
- Monthly stop: Track-S max -5% monthly loss triggers no new entries for remainder of month

---

## 4. Key Classes and Functions

### `feature_engine.py`
- `normalize_ohlcv(df)` → `pd.DataFrame` — canonicalizes any OHLCV variant to flat columns
- `make_synthetic_ohlcv(n, seed)` → `pd.DataFrame` — deterministic synthetic price series for tests
- `TechnicalIndicators(df)` — vectorized indicator builder
  - `.build(horizon, feature_lag=1)` → `FeatureBuildResult(frame, feature_columns, target_columns)`
  - `.build_all(horizon)` → full feature matrix
- `feature_columns()` → list[str] — returns the canonical feature column names

### `ensemble_model.py`
- `ModelConfig` dataclass — `horizon`, `seq_len`, `n_splits`, `gap`, `model_kind`, `xgb_device`, `prefer_gpu`, `use_xgboost`, `lite`, `use_lstm`, `xgb_weight`, `lstm_weight`, `random_state`, `xgb_params`
- `DirectionModel` — wraps XGBoost or LogisticRegression; `fit()`, `predict_proba()`, `feature_importance()`
- `EnsemblePredictor` — orchestrates walk-forward fitting; exposes `xgb` (backend string), `feature_importance()` (averaged across folds), `predict()` (OOF), `predict_final()` (fresh probs)
- `xgb_params_for_device(base, device)` → dict — version-aware XGBoost param mapping
- `_safe_auc(y_true, prob)` → float — returns 0.5 when only one class present

### `backtester.py`
- `BacktestConfig` dataclass — capital, transaction costs, slippage, Kelly fraction, thresholds, stop/TP percentages
- `Trade` dataclass — entry/exit index, price, quantity, value, PnL, exit_reason
- `BacktestResult` (dict subclass) — attributes for total_return_pct, sharpe_ratio, max_drawdown_pct, win_rate_pct, n_trades
- `Backtester` class — `.run(features, probabilities, prices) → BacktestResult`

### `risk_rules.py`
- `Gate` StrEnum — GREEN, AMBER, RED, ZERO
- `RiskConfig` frozen dataclass — total_capital (default $100k), track allocations, stop/TP percentages, score thresholds, position caps
- `CandidateVerdict` dataclass — ticker, track, score, gate, verdict, entry/stop/TP1/TP2, risk_reward, position sizing, reasons
- `portfolio_targets(cfg) → pd.DataFrame` — capital allocation summary
- `position_size_by_risk(entry, stop, track_capital, risk_per_trade_pct)` → (quantity, position_value, open_risk)
- `evaluate_track_s_candidate(score, probabilities, backtest_result, oof_coverage)` → CandidateVerdict
- `evaluate_track_l_candidate(...)` → CandidateVerdict (identical signature for future extension)

### `recommendation_engine.py`
- `RecommendationConfig` dataclass — universe, track, period, horizons, top_n, score thresholds, stop/TP defaults, min_rows, min_avg_dollar_volume
- `RecommendationEngine` — `.run() → list[CandidateVerdict]`, `.write_reports() → RecommendationRun`
- `parse_universe(universe_str)` → list[str]

### `data_providers.py`
- `DataProviderName` Literal — "auto", "synthetic", "yfinance", "openbb"
- `ProviderResult` dataclass — frame, provider_requested, provider_used, source, endpoint, fallback_reason
- `resolve_provider(data_provider, synthetic, provider_config)` → str
- `load_ohlcv_with_provider(ticker, period, synthetic, data_provider, provider_config, audit_logger)` → ProviderResult

### `reports.py`
- `now_stamp() → str` — "YYYY-MM-DD_HHMMSS"
- `ReportWriter(output_dir)` — `.daily_brief()`, `.risk_dashboard()`, `.track_l_thesis()`, `.monthly_scorecard()`, `.journal_append()`

### `hw_profile.py`
- `CommandResult`, `RuntimeStatus` frozen dataclasses
- `HW_PROFILE` dict — target machine (RTX 4060 Laptop, i5-13500HX), runtime machine info, optimization notes
- `runtime_status(include_tensorflow, include_xgboost) → RuntimeStatus`
- `print_hw_summary()`, `save_runtime_status(path)`

---

## 5. GPU / RTX 4060 Specifics

- **Target GPU**: NVIDIA GeForce RTX 4060 Laptop, 8 GB VRAM, Windows 11 + WSL2
- **TensorFlow GPU on Windows Native**: unsupported after TF 2.10; WSL2/CUDA is the recommended path
- **XGBoost GPU**: validated separately via `nvidia-smi` subprocess probe
- **CPU fallback**: always available; XGBoost CPU uses `tree_method=hist`
- **Environment variables** set at import: `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `TF_CPP_MIN_LOG_LEVEL=3`, `CUDA_DEVICE_ORDER=PCI_BUS_ID`
- **Effective worker calculation**: `max(1, min(16, os.cpu_count() - 2))`
- **Subprocess timeouts**: 12s for nvidia-smi, 30s for TensorFlow GPU smoke

---

## 6. Existing README Sections Found

- Current Status table (unified folder path, source deletion audit, file inventory, operator self-test, ops-v1 workflow, Phase 1 provider/audit upgrade, dashboard report bridge, default Python environment warning)
- Continue Quality Gates (8 checks under `.continue/checks/`)
- Commands section with `run.ps1` invocations for `self-test`, `recommend`, `ops-v1`, `dashboard-export`
- Verified Operator Path (observed self-test result: `PASS`, backend `xgb-cpu`, final capital `102190.84`)
- Phase 1 Provider And Audit Upgrade (provider table, OpenBB optional install, audit JSONL, recommendation engine OHLCV cache, MCP Phase 1 adapter contract scope)
- Dashboard Report Bridge (workflow, `dashboard-export` command, browser verification via `node dashboard\verify_bridge_smoke.mjs`, observed result: PASS)
- Ops v1 Manual Approval Workflow (`ops-v1` command, generated files, safety boundary)
- Structure tree diagram
- Validation references (`reports/validation_results.md`, `reports/consolidation_report.md`)
- Security Boundary (no broker API, no .env secrets, audit log masking, market data as data not instructions)
- Latest OpenBB Cache Smoke (observed `audit_log.jsonl` with 1 successful event)

---

## 7. Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ (verified with 3.12) |
| ML — primary | XGBoost (CPU/GPU via `hist`/`cuda` tree method, version-aware) |
| ML — fallback | scikit-learn LogisticRegression with StandardScaler + SimpleImputer |
| CV | sklearn.model_selection.TimeSeriesSplit with configurable `gap` |
| Data | pandas, numpy |
| CLI | argparse (subcommands) |
| Reports | pandas .to_markdown() for Markdown; native JSON |
| Optional providers | yfinance (default), OpenBB (`obb.equity.price.historical`) |
| Windows runner | PowerShell `run.ps1` selecting project `.venv` |
| Tests | pytest |
| Docs | Markdown (AGENTS.md, docs/, .continue/checks/) |
| Dashboard | `stock_pred_v5.jsx` React component + `dashboard_snapshot.json` bridge |
| Continue | PR-quality gate checks under `.continue/checks/` |
| Audit | JSONL via `audit_log.py` with secret masking |