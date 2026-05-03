# Review Round 1

## Components Checked

### RecommendationPanel.jsx
- `useEffect` with `load` in deps array — correct, no stale closure issue
- `fetch` uses relative path for FILE mode (`jsonPath`) and absolute `/api/recommend` for API mode
- Filter logic uses `includes` for verdict matching — appropriate
- `sort` by `score` and `rr` — both numeric, safe
- Error state shows retry button — good UX
- Footer renders `disclaimer` (truncated to 80 chars) — no risk of XSS
- **Risk**: `generated_at_utc` accessed as `snapshot.generated_at_utc || Date.now()` — schema uses `generated_at` per `dashboard_bridge` output. Will show current date instead of real timestamp. Non-blocking.

### RecommendationCard.jsx
- Self-imports `RiskGateBadge` (line 2: `import RiskGateBadge from "./RiskGateBadge"`) — **BUG**: should be the component in same dir, but the file is `RiskGateBadge.jsx`. This import will fail at runtime. This is critical.
- `fmtMoney` handles null — correct
- `fmtPct` adds sign — correct
- `onClick` is optional prop with conditional mouse handlers — correct immutable-safe pattern

### RiskGateBadge.jsx
- Verdict config map has 8 entries covering all known verdict types
- Unknown verdicts fall back to gray with `verdict || "N/A"` label — safe
- Inline styles only, no external data — no XSS risk
- No network calls — clean

### StockPredV5.jsx
- `import RecommendationPanel from "./components/RecommendationPanel"` — correct path
- REC tab added to tab bar at line 956
- `recSource` state initialized to `"file"` — safe default
- `RecommendationPanel` receives `jsonPath` or `apiUrl` based on `recSource` — correct toggle
- Vite proxy: `/api` → `http://127.0.0.1:5151` — matches Flask CORS origin

## Critical Issues

| # | File | Issue | Severity |
|---|------|--------|----------|
| 1 | `RecommendationCard.jsx:2` | Wrong self-import: `import RiskGateBadge from "./RiskGateBadge"` — missing file extension. JSX files with `.jsx` extension must be imported with `.jsx` or without extension in some bundlers. Will cause "Module not found" at runtime. | CRITICAL |

## Non-Critical Observations

- `RecommendationPanel.jsx` — `generated_at_utc` field name mismatch (schema uses `generated_at`). Dashboard still renders, falls back to `Date.now()`.
- CORS origin hardcoded to `localhost:5173` — fragile if port changes

## Verification Needed

- Fix RecommendationCard.jsx import (CRITICAL)
- Run `npm run build` to verify no module errors
- Browser check of REC tab (manual)

## Status

| Check | Result |
|-------|--------|
| Components compile | AMBER (import issue pending fix) |
| StockPredV5 integration | PASS |
| Vite proxy config | PASS |
| API CORS config | PASS |
| Dashboard snapshot schema | PASS |
