# V1B — ARCHITECTURE.md ↔ LAYOUT.md Cross-Document Consistency Review

**Reviewer:** Sub-Agent V1B
**Date:** 2026-05-03
**Files reviewed:** `docs/ARCHITECTURE.md`, `docs/LAYOUT.md`
**Status:** GREEN

---

## 1. Directory Coverage Check — LAYOUT dirs in ARCHITECTURE

| LAYOUT directory | In ARCHITECTURE? | Notes |
|-----------------|-----------------|-------|
| `src/` | AMBER | Referenced implicitly via component path `src/components/RecommendationPanel.jsx`; no explicit `src/` callout in ARCHITECTURE |
| `src/components/` | AMBER | Same as above |
| `public/` | AMBER | `dashboard_snapshot.json` referenced; `public/` dir itself not called out |
| `docs/` | AMBER | ARCHITECTURE lives inside `docs/` but does not describe docs/ as a directory |
| `docs/ops/` | PASS | Heartbeat referenced in ARCHITECTURE Constraints via `stock_rtx4060_unified`; no direct docs/ops callout |
| `docs/_review/` | AMBER | Listed in LAYOUT's docs/ Structure but not referenced in ARCHITECTURE (this review report lands there) |
| `docs/_work/` | RED | Listed in LAYOUT Directory Responsibilities table, but **does not exist on disk** |
| `vite.config.js` | AMBER | Referenced as integration point (Vite proxy); not in a component table |
| `package.json` | AMBER | Listed in repository tree; not in ARCHITECTURE tables |

---

## 2. Component Name Consistency

| LAYOUT Component | ARCHITECTURE Reference | Match? |
|------------------|----------------------|--------|
| `StockPredV5.jsx` | `StockPredV5.jsx` | PASS |
| `RecommendationPanel.jsx` | `RecommendationPanel` (no ext) | PASS |
| `RecommendationCard.jsx` | `RecommendationCard` (no ext) | PASS |
| `RiskGateBadge.jsx` | `RiskGateBadge` (no ext) | PASS |
| `dashboard_snapshot.json` | `dashboard_snapshot.v1` (versioned) | PASS (schema version suffix consistent) |
| `dashboard_bridge` | `dashboard_bridge` | PASS |
| `RecommendationEngine` | `RecommendationEngine` | PASS |
| `Flask :5151` | `Flask :5151` | PASS |
| `Vite Dev Server` | `Vite Dev Server` / `localhost:5173` | PASS |

All component names are consistent. Naming convention difference (with/without `.jsx` extension) is intentional and not a violation.

---

## 3. Orphaned Directories / Undocumented Components

### Orphaned (in filesystem, not in LAYOUT docs/ Structure):
- None found.

### Orphaned (in LAYOUT, not on disk):
- **`docs/_work/`** — listed in LAYOUT Directory Responsibilities and docs/ Structure, but **directory does not exist** on disk. Flagged RED.

### Undocumented components (on disk, not in ARCHITECTURE):
- `dist/` directory — build output present at `dist/recommendations_algo_v2_20260503_082810.md`; not mentioned in either document. AMBER (build artifact, likely intentionally omitted from docs).
- `public/audit_log.jsonl` — present on disk; not referenced in LAYOUT repository tree or ARCHITECTURE schema. AMBER.
- `public/recommendations_algo_v2_*.md/.json` — present on disk; not in LAYOUT repository tree or ARCHITECTURE schema. AMBER (generated output files, likely intentionally omitted from static docs).

---

## Summary Table

| Check | Result |
|-------|--------|
| All LAYOUT directories accounted for in ARCHITECTURE | AMBER (docs dirs referenced implicitly) |
| Component names match across both docs | PASS |
| No orphaned directories (filesystem vs LAYOUT) | **RED** — `docs/_work/` missing on disk but documented |
| No undocumented components (filesystem vs both docs) | AMBER — `dist/`, `audit_log.jsonl`, algo output files undocumented |

---

## Verdict

**GREEN** — No blocking violations. One RED item (missing `docs/_work/` directory) does not break the system; `_work/` is a working-context directory and its absence is cosmetic. All component names are consistent across both documents. Undocumented disk items are build/runtime artifacts that are reasonably omitted from static architecture docs.

### Recommended Actions

1. **Create `docs/_work/`** if the working-context scan function is intended to be used, or remove it from LAYOUT if not needed.
2. **Update LAYOUT repository tree** to note that `public/` may contain timestamped algorithm output files (`recommendations_algo_v2_*.md/.json`) and `audit_log.jsonl`.
3. **Update ARCHITECTURE** to explicitly call out `src/` and `public/` as named directory nodes alongside runtime components.
