# STOCK·PRED v5.0 — Runbook

## Deployment

### Local Development

```bash
npm install
npm run dev
# → http://localhost:5173
```

### Preview Server (Unified Package)

```bash
cd ../stock_rtx4060_unified
.venv/Scripts/python.exe preview_server.py
# API: http://127.0.0.1:5151
# Vite: http://localhost:5173
```

### Production Build

```bash
npm run build
# Output: dist/
npm run preview
# Serves dist/ on port 4173
```

## Monitoring

### Health Checks

| Endpoint | URL | Expected |
|----------|-----|----------|
| Vite dev | `http://localhost:5173` | HTML page loads |
| Flask API | `http://127.0.0.1:5151/api/health` | `{"status":"ok"}` |

### REC Tab Verification

1. Open dashboard at `http://localhost:5173`
2. Click **REC** tab in right sidebar
3. Toggle **FILE** / **API** source
4. Verify recommendation cards render with verdicts (GREEN/AMBER/RED)

## Common Issues

### "vite not recognized"

**Cause**: Vite not installed in `stock-pred-v5/`

**Fix**:
```bash
cd stock-pred-v5
npm install
```

### API returns 500

**Cause**: Python venv missing Flask deps

**Fix**:
```bash
cd stock_rtx4060_unified
.venv/Scripts/pip install flask flask-cors
```

### CORS errors in browser

**Cause**: Flask CORS not configured for the Vite origin

**Fix**: Already configured in `api_server.py` for `localhost:5173`. Restart the API server.

### REC tab shows no data

**Cause**: Static JSON not found or API not running

**Fix**: Run Option C (`preview_server.py`) or check `public/dashboard_snapshot.json` exists

## Rollback

No formal rollback needed for local dev. For production deployments:

1. Keep previous `dist/` build
2. `npm run preview -- --port 4174` to test new build
3. Swap port in nginx/Caddy config
