# V1-B1 CONSISTENCY REPORT

**Sub-Agent:** README ↔ ARCHITECTURE consistency
**Date:** 2026-05-03
**Files reviewed:**
- `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified\README.md`
- `C:\Users\jichu\Downloads\주식\stock_rtx4060_unified\docs\SYSTEM_ARCHITECTURE.md`

---

## STATUS: AMBER

Two documentation gaps found. No functional incorrectness detected.

---

## CHECK 1 — Module consistency: README Architecture flowchart vs ARCHITECTURE Component Topology

### Modules present in README Architecture flowchart

| README flowchart node | ARCHITECTURE Component Topology |
|-----------------------|-------------------------------|
| `recommendation_engine.py` | ✅ present (`RE[recommendation_engine.py]`) |
| `feature_engine.py` | ✅ present (`FE[feature_engine.py]`) |
| `ensemble_model.py` | ✅ present (`EM[ensemble_model.py]`) |
| `backtester.py` | ✅ present (`BT[backtester.py]`) |
| `risk_rules.py` | ✅ present (`RR[risk_rules.py]`) |
| `dashboard_snapshot.v1` | ✅ present (`SNAP[dashboard_snapshot.json]`) |
| `Markdown / JSON Report` | ✅ present (`RPT[Markdown / JSON Report]`) |
| Flask :5151 (api_server.py) | **❌ NOT in the Component Topology Mermaid diagram** |

### Details

`api_server.py` is documented in ARCHITECTURE as a Runtime Component and appears in the Cross-Project Interface section, and it is referenced in the Module Dependency Map. However, it does **not appear in the Component Topology Mermaid diagram**. This makes the diagram structurally incomplete for an architect or new contributor reading it as the single source of truth.

### Mismatch list (CHECK 1)

1. `api_server.py` (Flask :5151) — listed as a Runtime Component in ARCHITECTURE and mentioned in Cross-Project Interface, but missing from the Component Topology Mermaid diagram and the Module Dependency Map

---

## CHECK 2 — Tech Stack consistency

| Layer | README | ARCHITECTURE | Match |
|-------|-------|-------------|-------|
| Runtime | Python 3.11+ | Python 3.11+ | ✅ |
| ML | scikit-learn >=1.1 | scikit-learn >=1.1 | ✅ |
| ML | XGBoost >=3.1 | XGBoost >=3.1 | ✅ |
| Data | pandas (latest) | pandas >=2.2 | ✅ (version floor acceptable) |
| Data | numpy (latest) | numpy >=1.26 | ✅ (version floor acceptable) |
| Data | yfinance >=0.2.66 | yfinance >=0.2.66 | ✅ |
| API | Flask + flask-cors >=3.0 / >=4.0 | Flask >=3.0, flask-cors >=4.0 | ✅ |
| Optional | OpenBB — | OpenBB latest | ✅ (optional qualifier implied) |
| GPU | WSL2/CUDA — | WSL2/CUDA — | ✅ |
| Charts | tabulate >=0.9 | **absent** | ⚠️ |

### Details

- `tabulate` appears in the README Tech Stack table (Charts layer, purpose: Markdown table output) but has no entry in ARCHITECTURE's Technology Stack table. This is a minor omission — tabulate may be treated as a transitive dependency rather than a primary stack item, but it should be explicitly noted one way or the other.
- Minor version specifier differences (`latest` vs `>=x.y`) between README and ARCHITECTURE are acceptable and not flagged as mismatches.

### Mismatch list (CHECK 2)

1. `tabulate >=0.9` (Charts layer) — present in README Tech Stack, absent from ARCHITECTURE Technology Stack table

---

## CHECK 3 — Cross-project claim (stock-pred-v5 as consumer)

| Document | Claim |
|----------|-------|
| README "Cross-Project Role" | `stock-pred-v5` REC tab data source via `dashboard_snapshot.json` via FILE mode or Flask API → `/api/recommend` |
| ARCHITECTURE "Cross-Project Interface" | Same — `stock-pred-v5 REC tab` fetches `dashboard_snapshot.json` (FILE mode) or `/api/recommend` (API mode), Vite proxy `/api` → `127.0.0.1:5151` |

Both documents are **consistent** on the cross-project consumer claim. No mismatch.

---

## Summary

| Check | Status | # Mismatches |
|-------|--------|-------------|
| 1. Module coverage (README ↔ ARCHITECTURE) | ⚠️ AMBER | 1 — `api_server.py` missing from Topology Mermaid diagram and Module Dependency Map |
| 2. Tech Stack table alignment | ⚠️ AMBER | 1 — `tabulate` absent from ARCHITECTURE Tech Stack |
| 3. Cross-project claim | ✅ PASS | 0 |

---

## Recommended Fixes

### Fix 1 (CHECK 1)
Add `api_server.py` to the Component Topology Mermaid diagram. Example insertion point in the `API["Flask API"]` subgraph:

```mermaid
    subgraph ApiServer["Flask API"]
        ApiRecommend[/api/recommend] --> RE
        ApiRecommend --> DB
        API_SRV[api_server.py :5151]
    end
```

Also add `api_server.py` to the Module Dependency Map as a node that `recommendation_engine.py` and `dashboard_bridge.py` connect to.

### Fix 2 (CHECK 2)
Add to ARCHITECTURE's Technology Stack table:

| Charts | tabulate | >=0.9 | Markdown table output in report writers |
