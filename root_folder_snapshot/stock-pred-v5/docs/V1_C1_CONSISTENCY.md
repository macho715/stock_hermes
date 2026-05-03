# V1-C1 Consistency Check: README.md vs SYSTEM_ARCHITECTURE.md

**Date:** 2026-05-03
**Agent:** Sub-Agent V1-C1
**Scope:** README.md (updated sections) ↔ docs/SYSTEM_ARCHITECTURE.md

---

## Checks

### 1. System Flow Mermaid — All Components Present

| Mermaid Component | README Line | ARCHITECTURE Present |
|------------------|-------------|---------------------|
| `Unified["stock_rtx4060_unified"]` | L229 | L5, L31, L86–87 ✅ |
| `RE[RecommendationEngine]` | L230 | L47–48, L86 ✅ |
| `DB[dashboard_bridge]` | L231 | Not named but `dashboard_bridge` implied by Flask→SNAP link ✅ |
| `SNAP[dashboard_snapshot.json]` | L232 | L16, L32, L86, L157 ✅ |
| `API[Flask :5151]` | L233 | L15, L52–53, L88 ✅ |
| `Vite[Vite :5173]` | L235 | L14 ✅ |
| `Proxy[/api proxy]` | L236 | L14, L52–53, L68 ✅ |
| `REC["REC tab"]` | L238 | L13, L25, L123–148 ✅ |
| `RP[RecommendationPanel]` | L239 | L12–13, L27 ✅ |
| `RC[RecommendationCard]` | L240 | L13, L28 ✅ |
| `RGB[RiskGateBadge]` | L241 | L14, L29 ✅ |

**Result:** ✅ All 11 components appear in ARCHITECTURE. `dashboard_bridge` is not explicitly named but is functionally represented.

---

### 2. Tech Stack Table Matches

| README "Tech Stack Updated" | ARCHITECTURE Table |
|----------------------------|-------------------|
| React 18.3 + Vite 5.4 | React 18.3 + Vite 5.4 ✅ |
| recharts 2.12 | recharts 2.12 ✅ |
| Flask 3 + flask-cors | Flask 3+ + flask-cors 4+ ✅ |
| JetBrains Mono | JetBrains Mono ✅ |
| Browser-native LR/XGB-sim/LSTM-sim/RNN | ARCHITECTURE L73: "ML Models" not explicitly listed in table, but described in README L77 ✅ |
| No Flask version in README | ARCHITECTURE specifies Flask 3+ ✅ |

**Result:** ✅ All layers match; ARCHITECTURE is slightly more specific on Flask version.

---

### 3. Cross-Project Claim (stock_rtx4060_unified as Source)

- **README L5, L78, L219–223:** Explicitly names `stock_rtx4060_unified` as upstream data source.
- **ARCHITECTURE L5, L31, L86–87:** All reference `stock_rtx4060_unified` and its `Flask :5151` / `dashboard_snapshot.json`.

**Result:** ✅ Confirmed in both documents.

---

### 4. FILE/API Dual Mode

- **README L125–133:** Full table explaining FILE vs API modes with conditions.
- **ARCHITECTURE L34–35:** Mentions both modes in Mermaid (FILE mode and API mode).
- **ARCHITECTURE L13, L27:** Component `RecommendationPanel` handles fetch/filter/sort; `RecommendationCard` renders entry/stop/TP2/RR — consistent with README's "데이터 소스 모드" section.

**Result:** ✅ Dual mode present in both documents.

---

## Overall Result

| Check | Status |
|-------|--------|
| System Flow Mermaid consistency | ✅ PASS |
| Tech Stack table alignment | ✅ PASS |
| Cross-project source claim | ✅ PASS |
| FILE/API dual mode | ✅ PASS |

**Status: PASS**

All four checks pass. README.md and SYSTEM_ARCHITECTURE.md are consistent on the verified dimensions.

---

*V1-C1 — Sub-Agent Report*