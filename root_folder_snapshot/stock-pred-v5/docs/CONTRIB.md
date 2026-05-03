# Contributing to STOCK·PRED v5.0

## Development Setup

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Scripts Reference

| Script | Description |
|--------|-------------|
| `npm run dev` | Start Vite dev server with hot reload (port 5173) |
| `npm run build` | Build production bundle to `dist/` |
| `npm run preview` | Serve production build locally (port 4173) |
| `npm start` | Alias for dev server |

## Project Structure

```
stock-pred-v5/
├── src/
│   ├── StockPredV5.jsx      # Main dashboard (US + KRX ML)
│   └── components/          # UI components
│       ├── RiskGateBadge.jsx      # Verdict color badge
│       ├── RecommendationCard.jsx # Individual rec card
│       └── RecommendationPanel.jsx # REC tab panel
├── public/
│   └── dashboard_snapshot.json  # Static recommendation data
├── vite.config.js           # Vite + React config, /api proxy
├── package.json
└── docs/
    ├── CONTRIB.md           # This file
    └── RUNBOOK.md           # Deployment & ops guide
```

## Environment Variables

This project uses a `.env` file (not committed; use `.env.example` as template):

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Flask API base URL | `http://127.0.0.1:5151` |
| `VITE_DEFAULT_CURRENCY` | Default display currency | `USD` |

Create `.env` in the project root:
```bash
VITE_API_URL=http://127.0.0.1:5151
VITE_DEFAULT_CURRENCY=USD
```

## Testing Procedures

```bash
# Smoke test: load dashboard at localhost:5173
npm run dev

# Check REC tab loads recommendation cards
open http://localhost:5173
# → Click REC tab in right sidebar

# API smoke test
curl http://127.0.0.1:5151/api/health
```

## Preview Server (Unified Package)

To run the full stack (API + Vite in one command), use the unified package:

```bash
cd ../stock_rtx4060_unified
.venv/Scripts/python.exe preview_server.py
```

This starts:
1. Flask API on port 5151
2. Vite dev server on port 5173
3. Opens browser automatically

## Adding Components

1. Create component in `src/components/`
2. Export from `src/components/index.js` (create if missing)
3. Import in `StockPredV5.jsx`
