# Spec

## Problem Statement

Users need to see algorithm-ranked stock-candidate recommendations alongside ML price predictions on the same dashboard, without switching between the `stock-pred-v5` React app and the `stock_rtx4060_unified` Python package.

## Goals / KPIs

| Goal | Metric | Target |
|------|--------|--------|
| REC tab renders recommendations | Cards displayed in browser | ≥ 0 cards |
| FILE mode works without API | REC tab loads with FILE toggle | JSON fetched |
| API mode fetches live data | REC tab loads with API toggle | Snapshot returned |
| Unified preview launches both servers | `preview_server.py` exit code | 0 |
| Docs cover dev + ops workflow | Files present | 7 docs |

## In Scope

- REC tab integration into `StockPredV5.jsx` right sidebar
- Three React components: `RiskGateBadge`, `RecommendationCard`, `RecommendationPanel`
- Static file mode (FILE): fetch `public/dashboard_snapshot.json`
- API mode (API): fetch via Vite `/api` proxy → Flask `127.0.0.1:5151`
- Vite proxy configuration for `/api` → `127.0.0.1:5151`
- Flask API server (`api_server.py`) with CORS
- Unified preview launcher (`preview_server.py`)
- Full documentation set (7 docs per project-doc-governor)

## Out of Scope

- Broker order execution, auto buy/sell
- Margin, options, short selling, leveraged ETF features
- User authentication / auth0
- Real-time WebSocket streaming
- Non-localhost deployment (prod server config)
- GPU acceleration in this package (lives in `stock_rtx4060_unified`)

## Interfaces / Data Contracts

### `dashboard_snapshot.v1` JSON Schema
```json
{
  "version": "dashboard_snapshot.v1",
  "generated_at": "ISO8601",
  "source": "stock_rtx4060_unified",
  "results": [{
    "ticker": "SYNTH-A",
    "track": "S",
    "verdict": "ELIGIBLE_RECOMMENDATION",
    "score": 82.5,
    "probability": 0.67,
    "expected_value": 7.2,
    "entry": 150.00,
    "stop": 144.00,
    "tp2": 165.00,
    "risk_reward": 3.50,
    "risk_budget": 375.00,
    "max_position": 3750.00,
    "suggested_qty": 25,
    "confirmations": ["DATA_ROWS", "LIQUIDITY", "MODEL_EDGE"],
    "validations": { "DATA_ROWS": "PASS", "LIQUIDITY": "PASS", "MARKET_REGIME": "PASS" }
  }]
}
```

### API Endpoints
| Endpoint | Method | Params |
|----------|--------|--------|
| `/api/health` | GET | — |
| `/api/recommend` | GET | `universe`, `track` (S/L/BOTH), `period`, `top`, `synthetic`, `model_kind` |
| `/api/snapshot` | GET | `path` (absolute JSON path) |

### Verdict Types
| Verdict | Color | Meaning |
|---------|-------|---------|
| `ELIGIBLE_RECOMMENDATION` | Green | Execution-ready candidate |
| `ACCUMULATE_RECOMMENDATION` | Green | Long-term accumulation candidate |
| `AMBER_REVIEW_ONLY` | Amber | Review only, not execution-ready |
| `AMBER_WATCHLIST` | Amber | Watch list only |
| `RED_NOT_RECOMMENDED` | Red | Blocked |
| `ZERO_RISK_PLAN_FAILED` | Gray | Risk plan structure failed |

## Acceptance Criteria

1. **REC tab visible**: Clicking the REC tab in the right sidebar renders recommendation cards
2. **FILE mode**: Toggling FILE shows `dashboard_snapshot.json` cards without API server
3. **API mode**: Toggling API calls `/api/recommend` and renders the returned snapshot
4. **Source toggle**: Both FILE and API modes load distinct data sources correctly
5. **Verdict badges**: Each card shows `RiskGateBadge` with correct color per verdict type
6. **Preview server**: `python preview_server.py` starts both Flask (port 5151) and Vite (port 5173)
7. **CORS healthy**: API health check returns `{"status":"ok"}` from `localhost:5151`

## Assumptions
- Assumption: Users run both servers on the same Windows machine (`localhost` access)
- Assumption: `stock-pred-v5` is always served via Vite dev server (port 5173), not a production host
- Assumption: `dashboard_snapshot.json` is generated externally and placed in `public/` before dashboard load

## Open Issues
- REC tab browser smoke test not yet independently verified (manual user check pending)
- CORS origin hardcoded to `localhost:5173` — fragile if Vite port changes
- No authentication on Flask API — not suitable for multi-user or exposed deployment
