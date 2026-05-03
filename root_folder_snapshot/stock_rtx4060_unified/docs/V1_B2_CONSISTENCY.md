# V1-B2 Consistency Report: ARCHITECTURE vs LAYOUT

**Scope:** `stock_rtx4060_unified` — `docs/SYSTEM_ARCHITECTURE.md` vs `docs/LAYOUT.md`
**Date:** 2026-05-03
**Status:** AMBER

---

## 1. Every module in ARCHITECTURE's Component table appears in LAYOUT's source tree

All 14 entries in ARCHITECTURE's Runtime Components table exist in `src/stock_rtx4060/`:

| Component | ARCHITECTURE path | LAYOUT entry | Actual path | Match |
|---|---|---|---|---|
| CLI Entry | `main.py` (root) | `main.py` | `main.py` | OK |
| Package CLI | `src/.../main.py` | `main.py` | `src/stock_rtx4060/main.py` | OK |
| Orchestrator | `recommendation_engine.py` | `recommendation_engine.py` | `src/stock_rtx4060/recommendation_engine.py` | OK |
| Feature Engine | `feature_engine.py` | `feature_engine.py` | `src/stock_rtx4060/feature_engine.py` | OK |
| Ensemble Model | `ensemble_model.py` | `ensemble_model.py` | `src/stock_rtx4060/ensemble_model.py` | OK |
| Backtester | `backtester.py` | `backtester.py` | `src/stock_rtx4060/backtester.py` | OK |
| Risk Rules | `risk_rules.py` | `risk_rules.py` | `src/stock_rtx4060/risk_rules.py` | OK |
| Dashboard Bridge | `dashboard_bridge.py` | `dashboard_bridge.py` | `src/stock_rtx4060/dashboard_bridge.py` | OK |
| **API Server** | **`src/stock_rtx4060/api_server.py`** | **`api_server.py`** (root, Key Entry Points) | **`api_server.py` (root)** | **MISMATCH** |
| Reports Writer | `reports.py` | `reports.py` | `src/stock_rtx4060/reports.py` | OK |
| Data Providers | `data_providers.py` | `data_providers.py` | `src/stock_rtx4060/data_providers.py` | OK |
| Audit Log | `audit_log.py` | `audit_log.py` | `src/stock_rtx4060/audit_log.py` | OK |
| Ops Workflow | `ops_workflow.py` | `ops_workflow.py` | `src/stock_rtx4060/ops_workflow.py` | OK |
| HW Profile | `hw_profile.py` | `hw_profile.py` | `src/stock_rtx4060/ops_workflow.py` | OK |
| MCP Adapter | `mcp_adapter.py` | `mcp_adapter.py` | `src/stock_rtx4060/mcp_adapter.py` | OK |
| Tests | `tests/test_*.py` | `tests/test_*.py` | `tests/test_core.py`, `test_data_providers.py`, `test_audit_log.py`, `test_mcp_adapter.py`, `test_dashboard_bridge.py` | OK |
| Continue checks | `.continue/checks/*.md` | `.continue/checks/` | Present | OK |

**Result: 15/16 match. 1 mismatch — `api_server.py` path.**

---

## 2. Every directory in LAYOUT's tree is reflected in ARCHITECTURE (or noted as appropriate)

| LAYOUT directory | ARCHITECTURE coverage |
|---|---|
| `src/stock_rtx4060/` | Covered (all 14 modules listed) |
| `tests/` | Covered |
| `docs/` | Covered |
| `.continue/checks/` | Covered |
| `dashboard/` | Covered (dashboard_bridge + bridge_smoke.html) |
| `config/` | Covered (provider config note) |
| `reports/` | Covered (runtime output, audit JSONL) |
| `examples/` | Not mentioned in ARCHITECTURE |
| `workspaces/` | Not mentioned in ARCHITECTURE |
| `archive/original_inputs/` | Not mentioned in ARCHITECTURE |
| `review_needed/` | Not mentioned in ARCHITECTURE |
| `tools/` | Not mentioned in ARCHITECTURE |

`examples/`, `workspaces/`, `archive/`, `review_needed/`, `tools/` have no runtime or architectural significance; they are appropriate to leave undocumented.

**Result: All active source directories covered. Passive archive dirs appropriately omitted.**

---

## 3. Key Entry Points in LAYOUT match Component Topology in ARCHITECTURE

LAYOUT Key Entry Points vs ARCHITECTURE Component Topology:

| LAYOUT entry | ARCHITECTURE coverage |
|---|---|
| `main.py` (root) | CLI Entry (root main.py) + Package CLI (src/main.py) |
| `main.py --recommend` | Core Pipeline via `recommendation_engine.py` |
| `main.py --benchmark` | Covered by `benchmark.py` in Active Package Modules |
| `main.py --ops-v1` | `ops_workflow.py` in Component table |
| `main.py --dashboard-export` | `dashboard_bridge.py` in Component table |
| `main.py --env` | Covered via `hw_profile.py` (RuntimeStatus) |
| `preview_server.py` | Mentioned in LAYOUT File Naming Conventions + root Python files |
| `api_server.py` | **Covered in Component table but at wrong path (`src/stock_rtx4060/`)** |

**Result: All entry points documented. `api_server.py` entry is structurally documented but at incorrect path in ARCHITECTURE.**

---

## 4. `api_server.py` and `preview_server.py` — both docs placement

| File | ARCHITECTURE | LAYOUT | Actual filesystem |
|---|---|---|---|
| `api_server.py` | Listed under `src/stock_rtx4060/` (Runtime Components table, Mermaid dependency graph) | `api_server.py` in Key Entry Points (root level) | `api_server.py` at repo root |
| `preview_server.py` | Not explicitly listed in Runtime Components table | Named in File Naming Conventions; entry in Key Entry Points | `preview_server.py` at repo root |

Both `api_server.py` and `preview_server.py` are correctly placed at repo root in LAYOUT and on disk. ARCHITECTURE misplaces `api_server.py` as `src/stock_rtx4060/api_server.py` in its Runtime Components table but correctly shows it at root in the Module Dependency Map (which graphs `api_server.py --> recommendation_engine.py` without the `src/` prefix — a self-contradiction within the same doc).

---

## Findings Summary

### MISMATCH (causes AMBER)

**ARCHITECTURE `api_server.py` path error**
- ARCHITECTURE Runtime Components table: `src/stock_rtx4060/api_server.py`
- LAYOUT Key Entry Points: `api_server.py` (root)
- Actual: `api_server.py` at repo root
- ARCHITECTURE Module Dependency Map: `api_server.py --> recommendation_engine.py` (correct root path, self-contradiction within ARCHITECTURE)

### MINOR GAPS (acceptable — passive dirs not covered in ARCHITECTURE)

- `examples/`, `workspaces/`, `archive/original_inputs/`, `review_needed/`, `tools/` not mentioned in ARCHITECTURE — appropriate, as they are non-runtime directories.

### CONSISTENT (PASS)

- All 14 `src/stock_rtx4060/` modules match exactly across both docs
- `benchmark.py` present and documented
- `preview_server.py` at root, referenced in both docs
- Test files and Continue checks fully covered
- Data flow, Component Topology Mermaid, and dependency graph are structurally correct (module path error in Runtime Components table aside)

---

## Fix Required

In `docs/SYSTEM_ARCHITECTURE.md`, **Runtime Components table row for "API Server"** should read:

```
| API Server | `api_server.py` (root) | Flask server (port 5151) for stock-pred-v5 integration |
```

Instead of the current:

```
| API Server | `src/stock_rtx4060/api_server.py` | Flask server (port 5151) for stock-pred-v5 integration |
```

No other files need movement or deletion. `preview_server.py` requires no doc fix.

---

**Status: AMBER** — 1 path mismatch in ARCHITECTURE Runtime Components table. All other checks PASS. Fix is one line in `docs/SYSTEM_ARCHITECTURE.md`.