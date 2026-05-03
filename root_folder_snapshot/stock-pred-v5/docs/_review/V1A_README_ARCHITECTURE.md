# V1A Review: README.md ↔ ARCHITECTURE.md — Cross-Document Consistency

**Reviewer:** Sub-Agent V1A — Cross-Document Consistency
**Date:** 2026-05-03
**Files:** `README.md` vs `docs/ARCHITECTURE.md`
**Result:** AMBER — 2 AMBER flags, 0 RED violations; action items required

---

## VERIFICATION 1: Module/Component Presence

| README mentions | ARCHITECTURE.md confirms | Status |
|----------------|--------------------------|--------|
| Flask API (`http://127.0.0.1:5151/api/recommend`) | "Flask API" at `127.0.0.1:5151` | PASS |
| Vite proxy (`/api` → `:5151`) | `vite.config.js` proxy: `/api` → `127.0.0.1:5151` | PASS |
| REC tab (4th tab) | "React REC tab" | PASS |
| `RecommendationPanel` | "RecommendationPanel" component | PASS |
| `RecommendationCard` | "RecommendationCard" in topology | PASS |
| `RiskGateBadge` | "RiskGateBadge" in topology | PASS |
| `dashboard_snapshot.json` | "dashboard_bridge → `dashboard_snapshot.v1`" + SNAP node | PASS |
| `RecommendationEngine` | "RecommendationEngine" at `stock_rtx4060_unified/src/` | PASS |
| `dashboard_bridge` | "dashboard_bridge" at `stock_rtx4060_unified/src/` | PASS |
| Vite Dev Server (`localhost:5173`) | "Vite Dev Server" at `localhost:5173` | PASS |

**Module/Component verdict: ALL PASS — 10/10**

---

## VERIFICATION 2: Technology Stack Consistency

| Item | README | ARCHITECTURE.md | Status |
|------|--------|-----------------|--------|
| React version | React 18.3 | React 18.3 | PASS |
| Vite version | Vite 5.4 | Vite 5.4 | PASS |
| Chart library | recharts 2.12 | recharts 2.12 | PASS |
| API framework | Flask (implied by port) | Flask 3 + flask-cors | PASS |
| Data schema | JSON (dashboard_snapshot) | dashboard_snapshot.v1 JSON | PASS |
| ML engine location | External (`stock_rtx4060_unified`) | stock_rtx4060_unified | PASS |

**Technology Stack verdict: ALL PASS — 6/6**

---

## VERIFICATION 3: Architecture Diagram Cross-Check

| Element | README Mermaid | ARCHITECTURE.md Mermaid | Status |
|---------|---------------|------------------------|--------|
| RecommendationEngine node | `RE[RecommendationEngine]` | `RE[RecommendationEngine]` | PASS |
| dashboard_bridge node | `DB[dashboard_bridge]` | `DB[dashboard_bridge]` | PASS |
| SNAP (dashboard_snapshot) | `SNAP[dashboard_snapshot.json]` | `SNAP[dashboard_snapshot.json]` | PASS |
| Flask API node | `API[Flask :5151]` | `API[Flask :5151]` | PASS |
| Vite node | `Vite[Vite :5173]` | `Vite` | PASS |
| Proxy node | `Proxy[/api proxy]` | `Proxy[/api proxy]` | PASS |
| REC tab node | `REC[REC tab]` | `REC[REC tab]` | PASS |
| RecommendationPanel | `RP[RecommendationPanel]` | `RP[RecommendationPanel]` | PASS |
| RecommendationCard | `RC[RecommendationCard]` | `RC[RecommendationCard]` | PASS |
| RiskGateBadge | `RGB[RiskGateBadge]` | `RGB[RiskGateBadge]` | PASS |
| FILE mode arrow | `SNAP -.->|"FILE mode"| RP` | `SNAP -.-> RP` | PASS* |
| API mode arrow | `API -.->|"API mode"| RP` | `API -.-> RP` | PASS* |

*Labels on dashed arrows differ in text but topology is identical.

**Architecture Diagram verdict: ALL PASS — 12/12**

---

## AMBER FLAGS (action recommended)

### AMBER-1: Main component path mismatch

| Document | Path | Note |
|----------|------|------|
| README | `src/StockPredV5.jsx` (1,688 LOC) | React mount + full ML dashboard |
| ARCHITECTURE.md | `src/components/RecommendationPanel.jsx` | REC tab only |

- **Risk:** Low. Both describe different granularity (README: entry point; ARCHITECTURE: REC subcomponent). The ARCHITECTURE.md is scoped to the REC tab integration, not the full dashboard. However, if someone searches `src/StockPredV5.jsx` expecting it to be documented, ARCHITECTURE.md is silent on it.
- **Recommendation:** ARCHITECTURE.md could add a note: "Full dashboard entry point: `src/StockPredV5.jsx` — REC tab integration is a sub-component of this."

### AMBER-2: ML inference scope contradiction

| Document | Claim |
|----------|-------|
| README | "모두 브라우저 내 추론, 외부 API 없음" (all browser-side inference, no external API) |
| ARCHITECTURE.md | "Flask 3 + flask-cors — Recommendation REST API" + stock_rtx4060_unified as ML engine |

- **Risk:** High for user confusion. The REC tab section of README describes the Flask API as a data source mode (API mode). However, the "기술 스택" (Technology Stack) section headline and the "ML 모델" section describe "no external API, all in-browser." The REC tab section is later in the file and partially contradicts the earlier framing.
- **Recommendation:** Clarify the README "핵심 기능" table or "기술 스택" section to distinguish: (a) price-prediction ML models = in-browser, (b) recommendation engine = Flask API. Example fix: add " recommendation engine via Flask API" to the ML 앙상블 row.

---

## RED VIOLATIONS

**None.**

---

## SUMMARY TABLE

| Check | PASS | AMBER | RED |
|-------|------|-------|-----|
| Module/Component presence | 10 | 0 | 0 |
| Technology stack consistency | 6 | 0 | 0 |
| Architecture diagram cross-check | 12 | 0 | 0 |
| **Total** | **28** | **2** | **0** |

---

## VERDICT

**Status: AMBER**

All 28 direct consistency checks pass. Zero RED violations.
Two AMBER flags require attention to prevent user confusion (ML inference scope framing, main component path).

### Required Actions

1. **[AMBER-1]** Add `src/StockPredV5.jsx` as entry point to ARCHITECTURE.md in a "Project Structure" or "Frontend Components" section.
2. **[AMBER-2]** Update README "기술 스택" or "핵심 기능" table to clarify that REC tab recommendation engine uses Flask API, separate from in-browser price-prediction ML.

### Files Touched
- `README.md` — AMBER-2 fix (clarification in 기술 스택 or 핵심 기능)
- `docs/ARCHITECTURE.md` — AMBER-1 fix (entry point note)

---
*V1A_README_ARCHITECTURE.md — Generated by Sub-Agent V1A*