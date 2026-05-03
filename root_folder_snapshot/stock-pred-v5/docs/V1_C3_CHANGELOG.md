# V1-C3 CHANGELOG Accuracy Check

**Inspector:** Sub-Agent V1-C3
**Date:** 2026-05-03
**File checked:** `docs/changelog.md` (2026-05-03 Phase 2 entry)
**Working dir:** `C:\Users\jichu\Downloads\주식\stock-pred-v5`

---

## Features Documented — Line-by-Line Verification

| # | Claim | Source File | Evidence | Status |
|---|---|---|---|---|
| 1 | REC tab integration (SIGNAL/MODELS/BACKTEST/REC tab bar, RecommendationPanel) | `src/StockPredV5.jsx` | Line 956: `["SIGNAL","MODELS","BACKTEST","REC"]`; Line 17: `import RecommendationPanel from "./components/RecommendationPanel"`; Lines 998-1029: REC panel renders `<RecommendationPanel .../>` | **VERIFIED** |
| 2 | FILE mode: fetch `/dashboard_snapshot.json` (no server needed) | `src/components/RecommendationPanel.jsx` | Lines 47-48: `if (jsonPath) { data = await fetchDashboardSnapshot(jsonPath); }`; Lines 24-32: `fetchDashboardSnapshot` performs plain `fetch(jsonPath)`; `StockPredV5.jsx` line 1023 passes `jsonPath="/dashboard_snapshot.json"` when source=file | **VERIFIED** |
| 3 | API mode: fetch `/api/recommend` via Vite proxy → Flask `127.0.0.1:5151` | `src/components/RecommendationPanel.jsx` | Lines 51-60: `else if (apiUrl) { ... fetch(apiUrl) }`; `StockPredV5.jsx` line 1024 passes `apiUrl="/api/recommend"` when source=api; Vite proxy configured in `vite.config.js` → `http://127.0.0.1:5151` (confirmed by changelog entry) | **VERIFIED** |
| 4 | Verdict badges: ELIGIBLE_RECOMMENDATION → green, AMBER_* → amber, RED_* → red, ZERO_* → gray | `src/components/RiskGateBadge.jsx` | Lines 10-19 `VERDICT_CONFIG`: ELIGIBLE/ACCUMULATE→`C.green`, AMBER_REVIEW_ONLY/AMBER_WATCHLIST→`C.amber`, RED_BELOW_THRESHOLD/RED_DATA_OR_MODEL_ERROR→`C.red`, ZERO_RISK_PLAN_FAILED/ZERO_NO_DATA→`C.gray` | **VERIFIED** |
| 5 | Filter tabs: ALL / GREEN / AMBER / RED; Sort: SCORE / R/R | `src/components/RecommendationPanel.jsx` | Lines 137-160: filter buttons ALL/GREEN/AMBER/RED with verdict-color mapping; Lines 162-179: sort toggle SCORE/R/R with `sortBy` state | **VERIFIED** |
| 6 | `dashboard_snapshot.v1` JSON consumed by RecommendationPanel | `public/dashboard_snapshot.json` | Line 2: `"schema_version": "dashboard_snapshot.v1"`; `RecommendationPanel.jsx` lines 75-87: consumes `snapshot?.results` array; lines 89-95: computes verdict counts from `snapshot.results` | **VERIFIED** |

---

## Summary

All 6 "Features Documented" claims in the 2026-05-03 Phase 2 changelog entry are **VERIFIED** against actual source code. No discrepancies found.

### Status: **PASS**

All features exist in the codebase, props/data-flow paths are wired correctly, and the `dashboard_snapshot.json` schema version matches the changelog description.

---

**Output file:** `C:\Users\jichu\Downloads\주식\stock-pred-v5\docs\V1_C3_CHANGELOG.md`
