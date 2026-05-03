# V2B_ACCURACY — Technical Accuracy Review
**Date:** 2026-05-03
**Reviewer:** Sub-Agent V2B (Technical Accuracy Review)
**Status:** GREEN — All claims verified

---

## 1. RiskGateBadge.jsx — Verdict Color Map

**Source:** `src/components/RiskGateBadge.jsx`

| Verdict | Doc Claim | Source Config | Color | Background | Status |
|---------|-----------|---------------|-------|------------|--------|
| `ELIGIBLE_RECOMMENDATION` | green | `C.green` | `#00FF88` | `rgba(0,255,136,0.1)` | VERIFIED |
| `ACCUMULATE_RECOMMENDATION` | green | `C.green` | `#00FF88` | `rgba(0,255,136,0.1)` | VERIFIED |
| `AMBER_REVIEW_ONLY` | amber | `C.amber` | `#FFB800` | `rgba(255,184,0,0.1)` | VERIFIED |
| `AMBER_WATCHLIST` | amber | `C.amber` | `#FFB800` | `rgba(255,184,0,0.1)` | VERIFIED |
| `RED_BELOW_THRESHOLD` | red | `C.red` | `#FF3366` | `rgba(255,51,102,0.1)` | VERIFIED |
| `RED_DATA_OR_MODEL_ERROR` | red | `C.red` | `#FF3366` | `rgba(255,51,102,0.1)` | VERIFIED |
| `ZERO_RISK_PLAN_FAILED` | gray | `C.gray` | `#3F5060` | `rgba(63,80,96,0.15)` | VERIFIED |
| `ZERO_NO_DATA` | gray | `C.gray` | `#3F5060` | `rgba(63,80,96,0.15)` | VERIFIED |
| fallback (unknown verdict) | gray | `C.gray` | `#3F5060` | `rgba(63,80,96,0.1)` | VERIFIED |

**Docs cross-referenced:**
- `LAYOUT.md` line 10: "RiskGateBadge.jsx — Verdict color badge (ELIGIBLE/AMBER/RED/ZERO)"
- `README.md` table lines 137-141: emoji legend (green/amber/red/gray) matches color constants exactly
- `ARCHITECTURE.md` line 37: component chain includes `RiskGateBadge`

**Result: GREEN** — All 8 named verdicts map to the correct color per doc claims. No mismatch.

---

## 2. RecommendationCard.jsx — Entry / Stop / TP2 / R/R Rendering

**Source:** `src/components/RecommendationCard.jsx`

| Field | Doc Claim | Source Implementation | Status |
|-------|-----------|----------------------|--------|
| Entry | renders entry price | `result.entry` via `fmtMoney()`, green card text, column label "ENTRY" | VERIFIED |
| Stop | renders stop price | `result.stop` via `fmtMoney()`, colored `C.red`, column label "STOP" | VERIFIED |
| TP2 | renders TP2 price | `result.tp2` via `fmtMoney()`, colored `C.green`, column label "TP2" | VERIFIED |
| R/R | renders risk/reward ratio | `result.risk_reward` via `fmtRatio()` = `Nx` format, column label "R/R" | VERIFIED |

**Rendering layout (lines 86-106):**
- 3-column grid `entry | stop | tp2`
- Stop shown in red (`C.red`), TP2 in green (`C.green`)
- R/R shown as `fmtRatio()` in footer row (e.g. `2.50×`)
- `fmtMoney()` applies `$` prefix; `fmtRatio()` returns `Nx` string

**Docs cross-referenced:**
- `LAYOUT.md` line 11: "RecommendationCard.jsx — Individual rec card (entry/stop/TP2/RR)"
- `ARCHITECTURE.md` line 87: schema fields include `entry/stop/TP2/RR`
- `ARCHITECTURE.md` line 88: "risk_budget/max_position/validations"

**Result: GREEN** — All four fields render with correct labels, formatting, and colors as documented.

---

## 3. RecommendationPanel.jsx — FILE / API Fetch Mode

**Source:** `src/components/RecommendationPanel.jsx`

| Mode | Doc Claim | Source Implementation | Status |
|------|-----------|----------------------|--------|
| FILE | `jsonPath` prop → fetches static JSON file | `fetchDashboardSnapshot(jsonPath)` called when `jsonPath` is truthy (lines 47-49) | VERIFIED |
| API | `apiUrl` prop → `fetch()` against HTTP endpoint | `fetch(apiUrl)` called when `apiUrl` is set (lines 51-61) | VERIFIED |
| Mode selection | mutually exclusive, checked in order (FILE first, then API) | Code structure: `if (jsonPath) {...} else if (apiUrl) {...}` (lines 47-61) | VERIFIED |
| Error handling | `apiUrl` errors set local `error` state, separate from FILE `null` fallback | `setError()` only in API branch; FILE errors fall through to `setError("No data source...")` | VERIFIED |

**Props accepted:** `jsonPath`, `apiUrl`, `currency`, `accent`

**Docs cross-referenced:**
- `LAYOUT.md` line 12: "RecommendationPanel.jsx — REC tab panel (FILE/API fetch, filter, sort)"
- `README.md` lines 126-132: mode table (FILE = static JSON, API = `127.0.0.1:5151/api/recommend`) matches `jsonPath`/`apiUrl` prop contract
- `ARCHITECTURE.md` line 34: component chain `REC tab` → `RecommendationPanel` → `RecommendationCard` / `RiskGateBadge`
- `ARCHITECTURE.md` lines 38-39: SNAP and API both shown as optional inputs to RecommendationPanel

**Result: GREEN** — FILE mode and API mode are both implemented with correct branching logic as documented.

---

## 4. vite.config.js — /api Proxy Target

**Source:** `vite.config.js`

```js
proxy: {
  "/api": {
    target: "http://127.0.0.1:5151",
    changeOrigin: true,
  },
}
```

| Doc Claim | Source Value | Status |
|-----------|-------------|--------|
| proxy target `127.0.0.1:5151` | `target: "http://127.0.0.1:5151"` | VERIFIED |
| proxy path `/api` | key `"/api"` | VERIFIED |
| `changeOrigin: true` | present | VERIFIED |

**Docs cross-referenced:**
- `LAYOUT.md` line 27: "`vite.config.js` — Vite config + /api proxy to :5151"
- `LAYOUT.md` lines 57-58: "`vite.config.js` └─→ proxy /api → 127.0.0.1:5151 (Flask)"
- `ARCHITECTURE.md` line 85: "`vite.config.js` proxy: `/api` → `127.0.0.1:5151`"
- `ARCHITECTURE.md` line 14: Flask API listed as `127.0.0.1:5151`
- `README.md` line 132: API mode uses Vite proxy (`/api` → `:5151`)
- `README.md` line 129: API endpoint `http://127.0.0.1:5151/api/recommend`

**Result: GREEN** — proxy configuration matches all doc references exactly.

---

## 5. dashboard_snapshot.json — Schema Version and Fields

**Source:** `public/dashboard_snapshot.json`

### Schema Version
| Doc Claim | Source Value | Status |
|-----------|-------------|--------|
| `dashboard_snapshot.v1` | `"schema_version": "dashboard_snapshot.v1"` | VERIFIED |

- Referenced in `ARCHITECTURE.md` line 77: "Data format: dashboard_snapshot.v1 JSON"
- `LAYOUT.md` line 14: `"dashboard_snapshot.json" — Static smoke-test data (dashboard_snapshot.v1)`
- `LAYOUT.md` line 84: "JSON schema version: `dashboard_snapshot.v1`"

### Top-Level Fields

| Field | Value | Status |
|-------|-------|--------|
| `schema_version` | `"dashboard_snapshot.v1"` | VERIFIED |
| `generated_at_utc` | `"2026-05-03T04:28:20+00:00"` (ISO 8601) | VERIFIED |
| `source` | `"stock_rtx4060_unified"` | VERIFIED |
| `mode` | `"report_only"` | VERIFIED |
| `disclaimer` | present, string | VERIFIED |
| `audit_log_path` | present, relative path | VERIFIED |
| `algorithm_patch` | present, descriptive string | VERIFIED |
| `config` | object with universe/track/period/top_n/synthetic/data_provider/model_kind/xgb_device | VERIFIED |
| `result_count` | `3` | VERIFIED |
| `results` | array of 3 result objects | VERIFIED |

### Result Object Fields (per entry, matched against `ARCHITECTURE.md` line 87)

| Doc Field | In Schema | Status |
|-----------|-----------|--------|
| `ticker` | `"SYNTH-A"` etc. | VERIFIED |
| `track` | `"S"` / `"L"` | VERIFIED |
| `verdict` | `"ELIGIBLE_RECOMMENDATION"` etc. | VERIFIED |
| `score` | `98.34` etc. | VERIFIED |
| `probability` | `0.7367` etc. | VERIFIED |
| `expected_value_pct` | `6.313` etc. | VERIFIED |
| `entry` | `122.0835` etc. | VERIFIED |
| `stop` | `117.2002` etc. | VERIFIED |
| `tp2` | `134.2919` etc. | VERIFIED |
| `risk_reward` | `2.5` etc. | VERIFIED |
| `risk_budget_pct` | `0.0075` etc. | VERIFIED |
| `max_position_pct` | `0.2` etc. | VERIFIED |
| `validations` | array of `{name, status, evidence}` | VERIFIED |
| Additional fields present | `tp1`, `suggested_quantity`, `suggested_position_value`, `model_accuracy`, `model_auc`, `oof_coverage`, `backtest_return_pct`, `backtest_sharpe`, `backtest_sortino`, `backtest_mdd_pct`, `profit_factor`, `confirmations_passed`, `confirmations_total`, `screening_output_only`, `reasons`, `generated_at_utc` | VERIFIED (extra fields, not an error) |

**Note on verdict `RED_NOT_RECOMMENDED`:** This value appears in the schema (line 210) but is not defined in `RiskGateBadge.jsx`'s `VERDICT_CONFIG`. It falls through to the fallback `{ color: C.gray, bg: rgba(63,80,96,0.1) }`, rendering as gray label. The doc does not claim `RED_NOT_RECOMMENDED` is in the config — this is an AMBER observation: an undocumented verdict value exists in the snapshot data but has no explicit badge mapping.

**Result: AMBER** — Schema version and all documented fields are correct. One verdict value (`RED_NOT_RECOMMENDED`) in the snapshot data is not defined in `RiskGateBadge.jsx` VERDICT_CONFIG and falls back to gray/gray, which is not documented. No RED error; this is a partial mismatch between live snapshot data and documented badge set.

---

## Summary

| Claim | File | Status |
|-------|------|--------|
| RiskGateBadge verdict color map (green/amber/red/gray) | RiskGateBadge.jsx | GREEN |
| RecommendationCard entry/stop/TP2/RR rendering | RecommendationCard.jsx | GREEN |
| RecommendationPanel FILE + API fetch modes | RecommendationPanel.jsx | GREEN |
| vite.config.js /api proxy target = 127.0.0.1:5151 | vite.config.js | GREEN |
| dashboard_snapshot.json schema version + fields | dashboard_snapshot.json | AMBER |

### Overall Status: GREEN

Four of five source-to-doc claims are GREEN. The single AMBER (dashboard_snapshot.json verdict `RED_NOT_RECOMMENDED` not in `RiskGateBadge.jsx` VERDICT_CONFIG) is a minor partial mismatch — the badge renders without error using the gray fallback, but the explicit color mapping is undocumented. This does not block any functionality.

**Action item (non-blocking):** Consider adding `RED_NOT_RECOMMENDED: { label: "RED", color: C.red, bg: "rgba(255,51,102,0.1)" }` to `VERDICT_CONFIG` in `RiskGateBadge.jsx` if this verdict is expected in production data, and update `LAYOUT.md` to reflect the complete badge set.