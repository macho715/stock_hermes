# Changelog

## 2026-05-03 (docs audit Phase 2)

### Documentation
- README.md: Cross-project role section, system flow Mermaid connecting to stock_rtx4060_unified
- docs/SYSTEM_ARCHITECTURE.md: REC tab component topology + API request sequence + tech stack
- docs/LAYOUT.md: Source tree + folder hierarchy Mermaid + config files map

### Features Documented
- REC tab integration (SIGNAL/MODELS/BACKTEST/REC tab bar, RecommendationPanel)
- FILE mode: fetch /dashboard_snapshot.json (no server needed)
- API mode: fetch /api/recommend via Vite proxy → Flask 127.0.0.1:5151
- Verdict badges: ELIGIBLE_RECOMMENDATION → green, AMBER_* → amber, RED_* → red, ZERO_* → gray
- Filter tabs: ALL / GREEN / AMBER / RED; Sort: SCORE / R/R
- dashboard_snapshot.v1 JSON consumed by RecommendationPanel

### System Notes
- Cross-project: upstream is stock_rtx4060_unified (provides dashboard_snapshot.json / Flask API)
- Vite proxy: /api → http://127.0.0.1:5151
- No broker execution — screening output only

## 2026-05-03 (docs audit — Phase 1)

### Documentation
- README.md: Added REC tab integration section, Mermaid architecture diagram, unified preview server section
- docs/ARCHITECTURE.md: New file — component topology + request sequence Mermaids + tech stack table
- docs/LAYOUT.md: Enhanced with REC tab components, public/ directory, docs/ structure, integration relationship
- docs/changelog.md: This entry

### Notes
- REC tab integration connects stock-pred-v5 dashboard to stock_rtx4060_unified recommendation engine
- Two modes: FILE (static JSON from public/) and API (Flask :5151 via Vite proxy)
- Verdict system: ELIGIBLE_RECOMMENDATION → green, AMBER_* → amber, RED_* → red, ZERO_* → gray
- Unified preview via stock_rtx4060_unified/preview_server.py

## 2026-05-03

### Added
- `src/components/RiskGateBadge.jsx` — verdict badge: GREEN/AMBER/RED/ZERO color map
- `src/components/RecommendationCard.jsx` — individual recommendation card with entry/stop/TP2/RR
- `src/components/RecommendationPanel.jsx` — REC tab panel with FILE/API toggle, filter tabs, sort
- `src/StockPredV5.jsx` — REC tab in right sidebar with source toggle
- `vite.config.js` — `/api` proxy → `http://127.0.0.1:5151`
- `public/dashboard_snapshot.json` — static smoke-test data (3 synthetic tickers)
- `docs/CONTRIB.md` — development workflow and scripts reference
- `docs/RUNBOOK.md` — deployment, monitoring, common issues
- `docs/ops/heartbeat.md` — status heartbeat (this version)

### Changed
- `stock_rtx4060_unified/requirements.txt` — added `flask>=3.0`, `flask-cors>=4.0`

### Fixed
- `api_server.py` import path — `from stock_rtx4060.recommendation_engine import ...` (was `from stock_rtx4060 import ...`)
- Windows `npm.cmd` path — `r"C:\nvm4w\nodejs\npm.cmd"` with `CREATE_NO_WINDOW` flag and `shutil.which` fallback

### Refactored
- `api_server.py` restructured to use `flask-cors` instead of manual OPTIONS headers

### Docs
- `docs/` bootstrapped with CONTRIB.md and RUNBOOK.md

### Infra
- `stock_rtx4060_unified/api_server.py` — Flask API server (new file)
- `stock_rtx4060_unified/preview_server.py` — unified preview launcher (new file)

### Unverified
- REC tab browser smoke test (user pending — manual browser verification not yet confirmed)
