# V1-B3 CHANGELOG Accuracy Check — stock_rtx4060_unified

**Check date:** 2026-05-03
**Status:** AMBER (1 discrepancy found)

---

## Claim 1: Walk-forward ensemble with leak-safe TimeSeriesSplit(gap=horizon)

**VERIFIED**

- `ensemble_model.py` line 22: `from sklearn.model_selection import TimeSeriesSplit`
- `EnsemblePredictor._splitter()` (lines 274-277): `TimeSeriesSplit(n_splits=n_splits, gap=gap)`
- `EnsemblePredictor.__init__()` (lines 259-260): `self.config.gap = max(1, self.config.horizon)` when gap is None
- `recommendation_engine.py` line 267: `gap=cfg.cv_gap if cfg.cv_gap is not None else horizon`
- Walk-forward OOF probabilities stored in `oof_probabilities_`; gap-based purged splits confirmed in both `ensemble_model.py` and `recommendation_engine.py`

---

## Claim 2: 9 sequential risk gates

**VERIFIED**

All 9 gates present in `_validation_checks()` (recommendation_engine.py lines 542-604):

| # | Gate | Line | Status |
|---|---|---|---|
| 1 | DATA_ROWS | 544 | `len(df) >= cfg.min_rows` |
| 2 | LIQUIDITY | 545-551 | `avg_dollar_volume_20d >= min_avg_dollar_volume` |
| 3 | MARKET_REGIME | 553-559 | `regime_score >= 45|40` |
| 4 | MODEL_EDGE | 561-568 | `latest_prob >= 0.56|0.53` and `accuracy >= 0.50` |
| 5 | OOF_COVERAGE | 569-575 | `oof_coverage >= 0.45` |
| 6 | BACKTEST_SANITY | 577-584 | `mdd <= max_mdd_pct` and `sharpe >= -0.25` |
| 7 | RISK_PLAN | 585-593 | `stop < entry` and `rr >= 2.0|1.5` and `risk_budget_pct > 0` |
| 8 | TRACK_SCORE | 594-602 | `score >= green|amber threshold` |
| 9 | AUTOMATION_BOUNDARY | 603 | hardcoded PASS, checks `screening_output_only=True` |

---

## Claim 3: dashboard_bridge.py → dashboard_snapshot.v1 JSON schema

**VERIFIED**

- `dashboard_bridge.py` line 54: `"schema_version": "dashboard_snapshot.v1"`
- `build_dashboard_snapshot()` produces full v1 schema with `generated_at_utc`, `source`, `mode: "report_only"`, `disclaimer`, `audit_log_path`, `config`, `result_count`, `results[]`
- Each result entry includes all required fields and preserves `screening_output_only=True`

---

## Claim 4: api_server.py Flask API with /api/recommend, /api/snapshot, /api/health

**VERIFIED**

- `api_server.py` exists at repo root
- `/api/recommend` (line 34): runs `RecommendationEngine`, returns `dashboard_snapshot.v1`
- `/api/snapshot` (line 81): serves existing recommendation JSON as snapshot
- `/api/health` (line 96): returns `{"status": "ok", "service": "stock_rtx4060_unified", "version": "5.0.0"}`
- CORS enabled for `localhost:5173` (Vite proxy target)
- Imports `build_dashboard_snapshot` from `stock_rtx4060.dashboard_bridge`

---

## Claim 5: preview_server.py unified launcher (Flask thread + Vite subprocess + browser open)

**VERIFIED**

- `preview_server.py` exists at repo root
- Line 62: `threading.Thread(target=run_api, daemon=True)` starts Flask API on port 5151
- Line 34-57: `run_vite()` calls `npm --prefix <VITE_APP> run dev` (subprocess)
- Line 69: `webbrowser.open(vite_url)` opens `http://localhost:5173`
- Vite app path resolves to `ROOT.parent / "stock-pred-v5"`

---

## SYSTEM_ARCHITECTURE.md vs CHANGELOG consistency

### Minor discrepancy: api_server.py location in SYSTEM_ARCHITECTURE.md

| Document | Claim |
|---|---|
| CHANGELOG | `api_server.py` (root) |
| SYSTEM_ARCHITECTURE.md "Runtime Components" table | `src/stock_rtx4060/api_server.py` |

**Actual file location:** `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified\api_server.py` (root)

The `api_server.py` at root imports `src/stock_rtx4060/recommendation_engine` and `src/stock_rtx4060/dashboard_bridge`. It is NOT inside the package directory. The SYSTEM_ARCHITECTURE.md Runtime Components table misplaces it under `src/stock_rtx4060/`.

### All other SYSTEM_ARCHITECTURE.md claims verified

- Component topology (CLI → Provider → Features → Model → Backtest → Risk → DashboardBridge) — VERIFIED
- Sequence diagram participants and flow — VERIFIED
- Module dependency graph — VERIFIED
- Technology stack table — VERIFIED (Flask >=3.0, flask-cors >=4.0)
- Cross-project interface (dashboard_snapshot.v1, Vite proxy /api → :5151) — VERIFIED
- Walk-forward ensemble + feature_lag=1 — VERIFIED
- screening_output_only=True on all outputs — VERIFIED

---

## Summary

| Claim | Result |
|---|---|
| Walk-forward ensemble TimeSeriesSplit(gap=horizon) | VERIFIED |
| 9 sequential risk gates | VERIFIED |
| dashboard_bridge.py → dashboard_snapshot.v1 | VERIFIED |
| api_server.py endpoints | VERIFIED |
| preview_server.py unified launcher | VERIFIED |
| SYSTEM_ARCHITECTURE.md matches CHANGELOG | AMBER (1 misplacement) |

**Status: AMBER** — one minor documentation discrepancy in SYSTEM_ARCHITECTURE.md: the Runtime Components table lists `api_server.py` under `src/stock_rtx4060/` but the file is at the repo root. All five CHANGELOG feature claims are fully verified against source code.

**Recommended fix:** In `docs/SYSTEM_ARCHITECTURE.md`, move `api_server.py` from the `src/stock_rtx4060/` row to a separate root-level entry or note it as `api_server.py (root)` alongside `preview_server.py (root)`.
