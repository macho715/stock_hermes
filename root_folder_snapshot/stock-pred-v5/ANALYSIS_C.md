# ANALYSIS_C.md — stock-pred-v5 Deep Read

## 1. Project Purpose

stock-pred-v5 is a **dual-market client-side ML dashboard** for US (NYSE/NASDAQ) and KRX (Korea Exchange) equities. It pulls 6-month daily OHLCV data from Yahoo Finance (via `allorigins.win` proxy), computes technical indicators entirely in the browser, runs four lightweight ML models (LR, XGBoost-sim, LSTM-sim, Elman RNN), produces a weighted ensemble score, runs a $10,000 backtest simulation, and renders interactive charts + a ranked recommendation report. The primary product goal is auditable, screened candidate recommendations (not broker execution).

---

## 2. Component Structure

| File | Role |
|---|---|
| `src/StockPredV5.jsx` | Root dashboard — symbol selection, data fetching, indicator enrichment, 4-model inference, backtest, ENS scoring, tab routing (SIGNAL / MODELS / BACKTEST), chart rendering |
| `src/components/RecommendationPanel.jsx` | REC tab — fetches a pre-generated JSON snapshot (file path or HTTP API), renders filterable/sortable list of recommendation cards |
| `src/components/RecommendationCard.jsx` | Single recommendation row — ticker, verdict badge, score, entry/stop/TP2, R/R, position size, validation summary |
| `src/components/RiskGateBadge.jsx` | Inline verdict badge — ELIGIBLE/ACCUMULATE (green), AMBER (amber), RED/ZERO (red/gray) |

---

## 3. Data Flow

```
Yahoo Finance via allorigins proxy
  → raw OHLCV (6mo daily)
  → enrich() adds EMA(12/26/50), RSI(14), MACD(12/26/9), Bollinger(20,2σ)
  → features() extracts normalized feature vector per ticker
  → 4 models run client-side: lrPredict / xgbPredict / lstmPredict / rnnPredict
  → ENS = LSTM×30% + LR×25% + XGB×25% + RNN×20%
  → ENS ≥ 65 → BUY, ≤ 35 → SELL, 36–64 → HOLD
  → backtester: $10,000 sim, equity curve, Sharpe, trade log
  → RecommendationEngine (stock_rtx4060_unified) runs separately → JSON report
  → RecommendationPanel loads that JSON → renders REC tab cards
```

**RecommendationPanel input modes:**
- `jsonPath` prop → `fetch()` local/HTTP JSON file (e.g. `recommendation_reports/YYYYMMDD_report.json`)
- `apiUrl` prop → direct REST fetch (e.g. `http://127.0.0.1:5151/api/recommend`)

---

## 4. Tech Stack

| Layer | Technology |
|---|---|
| Framework | React 18.3.1 |
| Bundler | Vite 5.4.0 (`@vitejs/plugin-react`) |
| Charts | recharts 2.12.7 (ComposedChart, LineChart, BarChart, Area) |
| Styling | Inline JS objects (no CSS framework), JetBrains Mono font, dark terminal palette |
| Data source | Yahoo Finance v8 chart API via `api.allorigins.win` proxy |
| Fallback | `mulberry32` PRNG synthetic OHLCV (`SYN` badge) |
| ML models | Pure JS — Logistic Regression, XGBoost-sim (3 stumps), LSTM-sim (20-step), Elman RNN (15-step) |
| Proxy config | Vite dev server proxies `/api` → `http://127.0.0.1:5151` |

---

## 5. REC Tab Integration with stock_rtx4060_unified

The REC tab (`RecommendationPanel`) is designed to consume the structured JSON output of the sibling engine `stock_rtx4060_unified`:

- Expects JSON schema with fields: `generated_at_utc`, `schema_version`, `source`, `disclaimer`, `config { universe, track }`, `result_count`, `results[]`
- Each `result` entry: `ticker`, `track`, `verdict`, `score`, `probability`, `expected_value_pct`, `entry`, `stop`, `tp2`, `risk_reward`, `max_position_pct`, `suggested_quantity`, `confirmations_passed`, `confirmations_total`, `validations`
- Verdict labels: `ELIGIBLE_RECOMMENDATION`, `ACCUMULATE_RECOMMENDATION`, `AMBER_REVIEW_ONLY`, `AMBER_WATCHLIST`, `RED_BELOW_THRESHOLD`, `RED_DATA_OR_MODEL_ERROR`, `ZERO_RISK_PLAN_FAILED`, `ZERO_NO_DATA`
- Filter tabs: ALL / GREEN / AMBER / RED; sort by score or R/R
- Footer shows disclaimer + schema version + source
- No live model inference in REC tab — display only

---

## 6. Existing README Sections Found

The root `README.md` covers:
- Quick start (RUN.bat / npm install)
- Core features table (markets, data source, indicators, ML models, ensemble, backtest, benchmark, export)
- Sidebar tabs (SIGNAL, MODELS, BACKTEST)
- Folder structure (partial — truncated at line 60)

Additional docs under `docs/`:
- Architecture docs: `ARCHITECTURE.md`, `system-architecture.md`, `LAYOUT.md`, `plan.md`, `spec.md`
- Review docs: `docs/_review/` (V1A–V1D, V2A–V2C, review-round-1/2, FINAL_*)
- Ops docs: `docs/ops/heartbeat.md`, `docs/RUNBOOK.md`, `docs/CONTRIB.md`, `docs/changelog.md`
- Checklist: `docs/R1_B_DOCS_COMPLETE.md`
