# Cross-Project Architecture Map

## Relationship Matrix

| From | To | Relationship | Interface |
|------|----|-------------|-----------|
| continue-main | stock_rtx4060_unified | NONE | None — different monorepo, different purpose |
| continue-main | stock-pred-v5 | NONE | None — different monorepo, different purpose |
| stock_rtx4060_unified | stock-pred-v5 | PRODUCER → CONSUMER | `dashboard_snapshot.json` (file-based); consumed by REC tab in `stock-pred-v5` |

## Project Roles

| Project | Role | Type |
|---------|------|------|
| `continue-main` | VS Code AI coding assistant IDE plugin | TypeScript/Node monorepo — IDE extension, PR review agents |
| `stock_rtx4060_unified` | CLI stock-candidate screening and backtesting engine | Python CLI — produces ranked recommendation JSON/MD, dashboard snapshot |
| `stock-pred-v5` | Client-side ML equity dashboard | React/Vite JS app — OHLCV indicators, 4-model inference, backtest, REC tab |

---

## System Flow

```
stock_rtx4060_unified (Python CLI)
  └─> recommendation_engine.py
       └─> dashboard_bridge.py
            └─> writes dashboard_snapshot.json  (schema: dashboard_snapshot.v1)

stock-pred-v5 (React dashboard, stock_pred_v5.jsx)
  └─> src/components/RecommendationPanel.jsx
       └─> fetches dashboard_snapshot.json via fetch(jsonPath) or fetch(apiUrl)
            └─> renders REC tab cards with verdict badges, scores, risk plans
```

**Flow steps:**
1. Operator runs `run.ps1 recommend` (or `ops-v1`) in `stock_rtx4060_unified`
2. `recommendation_engine.py` produces `recommendations_algo_v2_*.json`
3. Operator runs `run.ps1 dashboard-export` to convert the recommendation JSON into `dashboard_snapshot.json`
4. `stock-pred-v5` user opens the React dashboard, switches to REC tab, and loads `dashboard_snapshot.json` via file-path or HTTP API endpoint
5. `RecommendationPanel` parses the snapshot and renders filterable/sortable recommendation cards

The data flow is **one-directional**: `stock_rtx4060_unified` writes a file; `stock-pred-v5` reads and displays it. There is no live model scoring in the REC tab — it is display-only.

---

## Shared Components

None identified. The three projects are independent packages with no shared libraries, no common dependencies, and no cross-repo imports.

| Shared component | Status |
|-----------------|--------|
| Shared utility modules | None |
| Shared data models | None (only JSON schema contract at the interface boundary) |
| Shared CI/CD | None |
| Shared environment | None |

The only shared artifact is the **JSON schema contract** (`dashboard_snapshot.v1`) written by `stock_rtx4060_unified` and parsed by `stock-pred-v5`.

---

## Interface Detail

### `dashboard_snapshot.json` (dashboard_snapshot.v1)

Produced by: `src/stock_rtx4060/dashboard_bridge.py` (`dashboard-export` CLI command)
Consumed by: `src/components/RecommendationPanel.jsx` in `stock-pred-v5`

Schema fields:
- `schema_version`, `generated_at_utc`, `source`, `screening_output_only`
- `results[]` — array of recommendation entries with: `ticker`, `track`, `verdict`, `score`, `probability`, `expected_value_pct`, `entry`, `stop`, `tp2`, `risk_reward`, `max_position_pct`, `suggested_quantity`, `confirmations_passed`, `confirmations_total`, `validations`
- `verdict` labels: `ELIGIBLE_RECOMMENDATION`, `ACCUMULATE_RECOMMENDATION`, `AMBER_REVIEW_ONLY`, `AMBER_WATCHLIST`, `RED_*`, `ZERO_*`

### `RecommendationPanel` input modes (stock-pred-v5)

| Mode | Prop | Description |
|------|------|-------------|
| Local/HTTP file | `jsonPath` | `fetch()` reads a local or remote `.json` file |
| REST API | `apiUrl` | `fetch()` hits `http://127.0.0.1:5151/api/recommend` (Vite dev proxy) |

The REC tab does not run model inference — it is a read-only display layer for `stock_rtx4060_unified` output.

---

## continue-main — Not Part of Stock System

`continue-main` is the monorepo for the [Continue](https://github.com/continuedev/continue) VS Code/JetBrains AI coding assistant plugin. It provides:

- Inline autocomplete and chat interface inside the IDE
- Configurable PR review agents (`.continue/checks/` YAML definitions)
- Diff analysis, next-edit suggestion, code indexing

It has **zero relationship** to the stock-candidate recommendation system. The only shared context is that both `stock_rtx4060_unified` and `stock-pred-v5` happen to use Continue as a PR-quality gate (`.continue/checks/` inside the `stock_rtx4060_unified` repo only). This is a development-tool relationship, not a data or runtime relationship.

---

## Summary

- `continue-main` is independent and unrelated — AI coding assistant plugin
- `stock_rtx4060_unified` and `stock-pred-v5` are coupled only via the `dashboard_snapshot.json` file contract
- Data flows one way: unified engine writes snapshot file, pred-v5 REC tab reads and displays it
- No shared code, no live API, no runtime dependency between the two stock projects
