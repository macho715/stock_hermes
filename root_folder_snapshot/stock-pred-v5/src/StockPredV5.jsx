import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  ComposedChart,
  LineChart,
  BarChart,
  Line,
  Bar,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  CartesianGrid,
  Legend,
} from "recharts";
import RecommendationPanel from "./components/RecommendationPanel";
// Executive Dashboard v2.1 — feature-flagged imports
const EXEC_LAYOUT = import.meta.env.VITE_DASHBOARD_LAYOUT === "executive";
import HeaderBar from "./components/HeaderBar";
import KpiCard from "./components/KpiCard";
import CurrentPriceCard from "./components/CurrentPriceCard";
import RecommendationKpi from "./components/RecommendationKpi";
import ConfidenceKpi from "./components/ConfidenceKpi";
import RiskRewardKpi from "./components/RiskRewardKpi";
import MarketSnapshotPanel from "./components/MarketSnapshotPanel";
import CompactPriceChart from "./components/CompactPriceChart";
import ModelScoresPanel from "./components/ModelScoresPanel";
import AiDecisionPanel from "./components/AiDecisionPanel";
import WatchlistPanel from "./components/WatchlistPanel";
import NewsTimelinePanel from "./components/NewsTimelinePanel";
import ScenarioOutlookPanel from "./components/ScenarioOutlookPanel";

/* ============================================================
 * STOCK·PRED v5.0  —  Dual-Market ML Dashboard
 * Markets: US (NYSE/NASDAQ) + KRX (Korea Exchange)
 * Models : Backend model evidence API · browser demo scores isolated from primary signal
 * Engine : Local stock_rtx4060 API-first real data path
 * ============================================================ */

const C = {
  bg: "#050A0E",
  bgDeep: "#02060A",
  panel: "#0A1218",
  panel2: "#0E1822",
  panelHi: "#13202C",
  // Upgraded: slightly warmer borders for visual separation
  border: "#1E3040",
  borderHi: "#2A4560",
  borderSoft: "#162330",
  text: "#D4E1EC",
  textDim: "#7A90A2",
  textMuted: "#3F5060",
  textLabel: "#A0B4C4",  // NEW: section/label text (brighter than muted)
  us: "#00CCFF",
  krx: "#FF6B35",
  buy: "#00FF88",
  sell: "#FF3366",
  hold: "#FFB800",
  lstm: "#BB66FF",
  lr: "#66CCFF",
  xgb: "#66FFAA",
  rnn: "#FF66AA",
  green: "#00FF88",
  red: "#FF3366",
  amber: "#FFB800",
  grid: "#152230",
  // NEW: subtle card elevation
  shadow: "0 2px 12px rgba(0,0,0,0.45), 0 1px 3px rgba(0,0,0,0.3)",
  shadowSm: "0 1px 6px rgba(0,0,0,0.35)",
  // NEW: loading/warning state softer
  warnBg: "#1A1200",
  warnBorder: "#3A2800",
  warnText: "#D4A800",
};

// Primary: monospace for data values, prices, codes
const FONT =
  '"JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, monospace';
// Secondary: sans-serif for labels, section headers, non-numeric UI
const FONT_SANS =
  '"Inter", "Segoe UI", system-ui, -apple-system, sans-serif';

const API_BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
const apiUrl = (path) => `${API_BASE}${path}`;
const DASHBOARD_CONFIG_PATH = "/dashboard_config.json";

function normalizeSymbolList(items) {
  if (!Array.isArray(items)) return [];
  return items
    .filter((item) => item && typeof item.symbol === "string" && item.symbol.trim())
    .map((item) => ({
      ...item,
      symbol: item.symbol.trim(),
      name: typeof item.name === "string" && item.name.trim() ? item.name.trim() : item.symbol.trim(),
    }));
}

function normalizeDashboardConfig(raw) {
  const markets = raw?.markets || {};
  return {
    markets: {
      US: { fallback_symbols: normalizeSymbolList(markets.US?.fallback_symbols) },
      KRX: { fallback_symbols: normalizeSymbolList(markets.KRX?.fallback_symbols) },
    },
    api_defaults: {
      symbol_period: String(raw?.api_defaults?.symbol_period || ""),
      symbol_data_provider: raw?.api_defaults?.symbol_data_provider || {},
      model_scores: raw?.api_defaults?.model_scores || {},
      model_scores_krx: raw?.api_defaults?.model_scores_krx || {},
      recommend: raw?.api_defaults?.recommend || {},
      recommend_krx: raw?.api_defaults?.recommend_krx || {},
    },
    signal_thresholds: raw?.signal_thresholds || {},
    model_quality: raw?.model_quality || {},
  };
}

async function fetchDashboardConfig() {
  const res = await fetch(DASHBOARD_CONFIG_PATH, { cache: "no-store" });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(payload.error || `dashboard config ${res.status}`);
  return normalizeDashboardConfig(payload);
}

/* ----------  Backend OHLCV API  ---------- */
const SYMBOL_FETCH_RETRY_DELAYS_MS = [250, 750];

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchSymbol(symbol, period, dataProvider) {
  let lastError = "backend API returned insufficient OHLCV rows";
  let lastErrorKind = "provider";

  for (let attempt = 0; attempt <= SYMBOL_FETCH_RETRY_DELAYS_MS.length; attempt++) {
    try {
      const params = new URLSearchParams({ symbol, period });
      if (dataProvider) params.set("data_provider", dataProvider);
      const local = apiUrl(`/api/symbol?${params.toString()}`);
      const localCtrl = new AbortController();
      const localTid = setTimeout(() => localCtrl.abort(), 12000);
      const localRes = await fetch(local, { signal: localCtrl.signal });
      clearTimeout(localTid);
      const localJson = await localRes.json().catch(() => ({}));
      if (!localRes.ok) {
        lastErrorKind = localRes.status >= 500 ? "network" : "provider";
        lastError = localJson.error || `backend API ${localRes.status}`;
      } else if (Array.isArray(localJson.data) && localJson.data.length >= 30) {
        return { data: localJson.data, source: localJson.source || "YFINANCE" };
      } else {
        lastErrorKind = "provider";
        lastError = "backend API returned insufficient OHLCV rows";
        break;
      }
    } catch (e) {
      lastErrorKind = "network";
      lastError = e.message || "backend API request failed";
    }

    if (attempt < SYMBOL_FETCH_RETRY_DELAYS_MS.length) {
      await sleep(SYMBOL_FETCH_RETRY_DELAYS_MS[attempt]);
    }
  }

  return { data: [], source: "ERROR", errorKind: lastErrorKind, error: lastError };
}

const MODEL_EVIDENCE_TIMEOUT_MS = 120000;
const MODEL_EVIDENCE_RETRY_DELAYS_MS = [750, 2000];

function modelEvidenceErrorMessage(error) {
  const message = String(error?.message || error || "");
  const name = String(error?.name || "");
  if (/abort/i.test(name) || /abort/i.test(message)) {
    return `model evidence request timed out after ${Math.round(MODEL_EVIDENCE_TIMEOUT_MS / 1000)}s`;
  }
  return message || "MODEL EVIDENCE UNAVAILABLE";
}

async function fetchModelEvidence(symbol, defaults) {
  const params = new URLSearchParams({
    symbol,
    ...defaults,
  });
  let lastError = null;
  for (let attempt = 0; attempt <= MODEL_EVIDENCE_RETRY_DELAYS_MS.length; attempt++) {
    const ctrl = new AbortController();
    const tid = setTimeout(() => {
      ctrl.abort(new DOMException("model evidence timeout", "TimeoutError"));
    }, MODEL_EVIDENCE_TIMEOUT_MS);
    try {
      const res = await fetch(apiUrl(`/api/model-scores?${params.toString()}`), {
        cache: "no-store",
        signal: ctrl.signal,
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok || payload.status !== "PASS") {
        throw new Error(payload.error || `model evidence API ${res.status}`);
      }
      return payload;
    } catch (e) {
      lastError = e;
      if (attempt < MODEL_EVIDENCE_RETRY_DELAYS_MS.length) {
        await sleep(MODEL_EVIDENCE_RETRY_DELAYS_MS[attempt]);
        continue;
      }
    } finally {
      clearTimeout(tid);
    }
  }
  throw new Error(modelEvidenceErrorMessage(lastError));
}

async function fetchUniverse(market) {
  const res = await fetch(apiUrl(`/api/universe?market=${encodeURIComponent(market)}`), { cache: "no-store" });
  if (!res.ok) throw new Error(`universe API ${res.status}`);
  const data = await res.json();
  if (!Array.isArray(data.symbols) || data.symbols.length === 0) {
    throw new Error("universe API returned no symbols");
  }
  return data;
}

async function fetchPaperStatus() {
  const res = await fetch(apiUrl("/api/paper-status"), { cache: "no-store" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `paper status API ${res.status}`);
  return data;
}

/* ----------  Indicators  ---------- */
function ema(v, p) {
  const k = 2 / (p + 1);
  const out = [v[0]];
  for (let i = 1; i < v.length; i++) out.push(v[i] * k + out[i - 1] * (1 - k));
  return out;
}
function sma(v, p) {
  const out = [];
  for (let i = 0; i < v.length; i++) {
    if (i < p - 1) { out.push(null); continue; }
    let s = 0;
    for (let j = i - p + 1; j <= i; j++) s += v[j];
    out.push(s / p);
  }
  return out;
}
function rsi(v, p = 14) {
  const out = new Array(v.length).fill(null);
  if (v.length < p + 1) return out;
  let g = 0, l = 0;
  for (let i = 1; i <= p; i++) {
    const d = v[i] - v[i - 1];
    if (d >= 0) g += d; else l -= d;
  }
  let aG = g / p, aL = l / p;
  out[p] = 100 - 100 / (1 + (aL === 0 ? 100 : aG / aL));
  for (let i = p + 1; i < v.length; i++) {
    const d = v[i] - v[i - 1];
    aG = (aG * (p - 1) + (d > 0 ? d : 0)) / p;
    aL = (aL * (p - 1) + (d < 0 ? -d : 0)) / p;
    out[i] = 100 - 100 / (1 + (aL === 0 ? 100 : aG / aL));
  }
  return out;
}
function macd(v) {
  const e12 = ema(v, 12), e26 = ema(v, 26);
  const line = v.map((_, i) => e12[i] - e26[i]);
  const sig = ema(line, 9);
  const hist = line.map((m, i) => m - sig[i]);
  return { line, sig, hist };
}
function bollinger(v, p = 20, k = 2) {
  const mid = sma(v, p);
  const up = [], lo = [];
  for (let i = 0; i < v.length; i++) {
    if (i < p - 1) { up.push(null); lo.push(null); continue; }
    let s = 0;
    for (let j = i - p + 1; j <= i; j++) s += (v[j] - mid[i]) ** 2;
    const sd = Math.sqrt(s / p);
    up.push(mid[i] + k * sd);
    lo.push(mid[i] - k * sd);
  }
  return { mid, up, lo };
}
function enrich(raw) {
  const c = raw.map((d) => d.close);
  const e12 = ema(c, 12), e26 = ema(c, 26), e50 = ema(c, 50);
  const r14 = rsi(c, 14);
  const m = macd(c);
  const bb = bollinger(c, 20, 2);
  return raw.map((d, i) => ({
    ...d,
    ema12: e12[i], ema26: e26[i], ema50: e50[i],
    rsi: r14[i],
    macd: m.line[i], macdSignal: m.sig[i], macdHist: m.hist[i],
    bbUpper: bb.up[i], bbMid: bb.mid[i], bbLower: bb.lo[i],
  }));
}

/* ----------  Feature extraction  ---------- */
function features(en, idx) {
  if (idx < 25) return null;
  const cur = en[idx];
  if (cur.rsi == null || cur.macdHist == null) return null;
  const p5 = en[idx - 5], p10 = en[idx - 10], p20 = en[idx - 20];
  const rsiNorm = (cur.rsi - 50) / 50;
  const macdNorm = cur.macdHist / Math.max(Math.abs(cur.close * 0.02), 0.001);
  const mom5 = (cur.close - p5.close) / p5.close;
  const mom10 = (cur.close - p10.close) / p10.close;
  const mom20 = (cur.close - p20.close) / p20.close;
  const bbPos = cur.bbUpper && cur.bbLower
    ? (cur.close - cur.bbLower) / Math.max(cur.bbUpper - cur.bbLower, 1e-6)
    : 0.5;
  const emaCross = (cur.ema12 - cur.ema26) / cur.close;
  let v5 = 0, v20 = 0;
  for (let i = idx - 4; i <= idx; i++) v5 += en[i].volume;
  for (let i = idx - 24; i <= idx - 5; i++) v20 += en[i].volume;
  const volRatio = v20 > 0 ? (v5 / 5) / (v20 / 20) - 1 : 0;
  return { rsiNorm, macdNorm, mom5, mom10, mom20, bbPos, emaCross, volRatio };
}

/* ----------  Activation helpers  ---------- */
const sigmoid = (x) => 1 / (1 + Math.exp(-Math.max(-30, Math.min(30, x))));
const tanh = (x) => Math.tanh(Math.max(-30, Math.min(30, x)));
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));

/* ----------  Models  ---------- */
function lrPredict(f) {
  if (!f) return 50;
  const z =
    1.8 * f.rsiNorm +
    1.4 * f.macdNorm +
    7.5 * f.mom5 +
    5.5 * f.mom10 +
    2.5 * f.mom20 +
    1.5 * (f.bbPos - 0.5) +
    24 * f.emaCross +
    1.1 * f.volRatio;
  return Math.round(sigmoid(z * 0.5) * 100);
}

function xgbPredict(f) {
  if (!f) return 50;
  let s = 50;
  // Stump 1: trend
  s += clamp(f.mom10 * 90 + f.emaCross * 180, -16, 16);
  // Stump 2: momentum
  s += clamp(f.rsiNorm * 11 + f.macdNorm * 9, -13, 13);
  // Stump 3: positioning
  s += clamp((f.bbPos - 0.5) * 22 + f.volRatio * 7 + f.mom5 * 60, -11, 11);
  return Math.round(clamp(s, 0, 100));
}

function lstmPredict(en, idx) {
  if (idx < 22) return 50;
  let h = 0, c = 0;
  const Wf = 0.45, Wi = 0.55, Wo = 0.5, Wc = 0.6;
  const Uf = 0.32, Ui = 0.42, Uo = 0.35, Uc = 0.5;
  const bi = 0.05, bf = 0.1;
  for (let t = idx - 19; t <= idx; t++) {
    const ret = (en[t].close - en[t - 1].close) / en[t - 1].close;
    const x = ret * 50;
    const fg = sigmoid(Wf * x + Uf * h + bf);
    const ig = sigmoid(Wi * x + Ui * h + bi);
    const og = sigmoid(Wo * x + Uo * h);
    const ct = tanh(Wc * x + Uc * h);
    c = fg * c + ig * ct;
    h = og * tanh(c);
  }
  const cur = en[idx];
  const tech =
    (cur.rsi != null ? (cur.rsi - 50) / 100 : 0) * 0.35 +
    (cur.macdHist || 0) / cur.close * 0.45;
  return Math.round(sigmoid((h + tech) * 1.6) * 100);
}

function rnnPredict(en, idx) {
  if (idx < 18) return 50;
  let h = 0;
  const Wx = 0.5, Wh = 0.42, b = 0.04;
  for (let t = idx - 14; t <= idx; t++) {
    const ret = (en[t].close - en[t - 1].close) / en[t - 1].close;
    const x = ret * 40;
    h = tanh(Wx * x + Wh * h + b);
  }
  const f = features(en, idx);
  const fb = f ? f.macdNorm * 0.3 + f.rsiNorm * 0.22 + f.mom5 * 5 : 0;
  return Math.round(sigmoid((h + fb) * 1.55) * 100);
}

function ensembleScore(s) {
  return Math.round(s.lstm * 0.30 + s.lr * 0.25 + s.xgb * 0.25 + s.rnn * 0.20);
}
function signalFromScore(s, thresholds) {
  const buy = Number(thresholds?.buy);
  const sell = Number(thresholds?.sell);
  if (Number.isFinite(buy) && s >= buy) return "BUY";
  if (Number.isFinite(sell) && s <= sell) return "SELL";
  return "HOLD";
}
function scoresFromModelEvidence(evidence) {
  if (!evidence || evidence.status !== "PASS" || !evidence.model_scores) return null;
  const main = Number(evidence.model_scores.main ?? evidence.ensemble_score);
  if (!Number.isFinite(main)) return null;
  return {
    main,
    lr: evidence.model_scores.logistic == null ? null : Number(evidence.model_scores.logistic),
    xgb: evidence.model_scores.xgboost == null ? null : Number(evidence.model_scores.xgboost),
    lstm: evidence.model_scores.lstm == null ? null : Number(evidence.model_scores.lstm),
    rnn: evidence.model_scores.rnn == null ? null : Number(evidence.model_scores.rnn),
  };
}

function getModelQualityWarning(evidence, qualityConfig) {
  const metrics = evidence?.evidence;
  if (!metrics) return null;
  const auc = Number(metrics.model_auc);
  const accuracy = Number(metrics.model_accuracy);
  const oofCoverage = Number(metrics.oof_coverage);
  const minAuc = Number(qualityConfig?.min_auc);
  const minAccuracy = Number(qualityConfig?.min_accuracy);
  const minOofCoverage = Number(qualityConfig?.min_oof_coverage);
  if (
    (Number.isFinite(auc) && Number.isFinite(minAuc) && auc < minAuc) ||
    (Number.isFinite(accuracy) && Number.isFinite(minAccuracy) && accuracy < minAccuracy) ||
    (Number.isFinite(oofCoverage) && Number.isFinite(minOofCoverage) && oofCoverage < minOofCoverage)
  ) {
    return qualityConfig?.warning || "MODEL QUALITY REVIEW ONLY";
  }
  return null;
}

/* ----------  Backtest  ---------- */
function runBacktest(en, thresholds) {
  const startIdx = 30;
  if (en.length < startIdx + 5) return null;
  const initial = 10_000;
  let cash = initial, shares = 0, pos = "CASH";
  const startPrice = en[startIdx].close;
  const bhShares = initial / startPrice;
  const eq = [];
  const trades = [];

  for (let i = startIdx; i < en.length; i++) {
    const f = features(en, i);
    const sc = {
      lr: lrPredict(f),
      xgb: xgbPredict(f),
      lstm: lstmPredict(en, i),
      rnn: rnnPredict(en, i),
    };
    const ens = ensembleScore(sc);
    const sig = signalFromScore(ens, thresholds);
    const px = en[i].close;
    if (sig === "BUY" && pos === "CASH") {
      shares = cash / px;
      cash = 0;
      pos = "LONG";
      trades.push({ date: en[i].date, action: "BUY", price: px, score: ens });
    } else if (sig === "SELL" && pos === "LONG") {
      cash = shares * px;
      shares = 0;
      pos = "CASH";
      trades.push({ date: en[i].date, action: "SELL", price: px, score: ens });
    }
    const ml = cash + shares * px;
    eq.push({
      date: en[i].date,
      timestamp: en[i].timestamp,
      ml: Math.round(ml * 100) / 100,
      bh: Math.round(bhShares * px * 100) / 100,
      score: ens,
      signal: sig,
    });
  }

  const finalPx = en[en.length - 1].close;
  const finalVal = pos === "LONG" ? shares * finalPx : cash;
  const bhFinal = bhShares * finalPx;
  const mlRet = (finalVal - initial) / initial;
  const bhRet = (bhFinal - initial) / initial;

  const dr = [];
  for (let i = 1; i < eq.length; i++) {
    dr.push((eq[i].ml - eq[i - 1].ml) / Math.max(eq[i - 1].ml, 1));
  }
  const avg = dr.reduce((a, b) => a + b, 0) / Math.max(dr.length, 1);
  const sd = Math.sqrt(
    dr.reduce((a, b) => a + (b - avg) ** 2, 0) / Math.max(dr.length, 1)
  );
  const sharpe = sd > 0 ? (avg / sd) * Math.sqrt(252) : 0;

  let wins = 0, done = 0;
  for (let i = 0; i < trades.length - 1; i++) {
    if (trades[i].action === "BUY" && trades[i + 1].action === "SELL") {
      done++;
      if (trades[i + 1].price > trades[i].price) wins++;
    }
  }
  const winRate = done > 0 ? wins / done : 0;

  return {
    eq, trades, initial, finalVal, bhFinal,
    mlRet, bhRet, alpha: mlRet - bhRet,
    sharpe, winRate,
    totalTrades: trades.length, completedTrades: done,
  };
}

/* ====================  COMPONENT  ==================== */
export default function StockPredV5() {
  const [market, setMarket] = useState("US");
  const [selected, setSelected] = useState("");
  const [dashboardConfig, setDashboardConfig] = useState(null);
  const [dashboardConfigError, setDashboardConfigError] = useState("");
  const [universeByMarket, setUniverseByMarket] = useState({ US: [], KRX: [] });
  const [universeSource, setUniverseSource] = useState("loading");
  const [universeError, setUniverseError] = useState("");
  const [cache, setCache] = useState({});
  const [symbolErrors, setSymbolErrors] = useState({});
  const [modelEvidenceCache, setModelEvidenceCache] = useState({});
  const [modelEvidenceErrors, setModelEvidenceErrors] = useState({});
  const [modelEvidenceLoading, setModelEvidenceLoading] = useState(false);
  // Executive layout — auto-fetched recommendation snap
  const [execSnap, setExecSnap] = useState(null);
  const [execSnapLoading, setExecSnapLoading] = useState(false);
  const [paperStatus, setPaperStatus] = useState(null);
  const [paperStatusError, setPaperStatusError] = useState("");
  const [paperStatusLoading, setPaperStatusLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("SIGNAL");
  const [recSource, setRecSource] = useState("api"); // "file" | "api"
  const [advisorEnabled, setAdvisorEnabled] = useState(false);
  const [lstmEnabled, setLstmEnabled] = useState(false);
  const [cmrsSizingEnabled, setCmrsSizingEnabled] = useState(false);
  const [bench, setBench] = useState({ open: false, rows: [], loading: false, progress: 0 });
  const [clock, setClock] = useState("");
  const [exportFlash, setExportFlash] = useState("");

  const symbols = universeByMarket[market] || [];
  const accent = market === "US" ? C.us : C.krx;
  const currency = market === "US" ? "$" : "₩";
  const fallbackSymbolsByMarket = useMemo(() => ({
    US: dashboardConfig?.markets?.US?.fallback_symbols || [],
    KRX: dashboardConfig?.markets?.KRX?.fallback_symbols || [],
  }), [dashboardConfig]);
  const symbolPeriod = dashboardConfig?.api_defaults?.symbol_period || "";
  const symbolProviderByMarket = dashboardConfig?.api_defaults?.symbol_data_provider || {};
  const symbolDataProvider = symbolProviderByMarket[market] || (market === "KRX" ? "pykrx" : "yfinance");
  // KRX uses pykrx provider; US uses yfinance. model_scores_krx overrides model_scores for KRX.
  const modelScoreDefaults = useMemo(() => {
    const base = dashboardConfig?.api_defaults?.model_scores || {};
    if (market === "KRX") {
      const krxOverride = dashboardConfig?.api_defaults?.model_scores_krx || {};
      return { ...base, ...krxOverride };
    }
    return base;
  }, [dashboardConfig, market]);
  const recApiDefaults = useMemo(() => {
    const base = dashboardConfig?.api_defaults?.recommend || {};
    if (market !== "KRX") return base;

    const krx = dashboardConfig?.api_defaults?.recommend_krx || {};
    const merged = {
      ...base,
      period: "5y",
      data_provider: "pykrx",
      ...krx,
    };
    const configuredTop = Number.parseInt(String(merged.top || ""), 10);
    const fullUniverseTop = symbols.length || 9;
    const top = Number.isFinite(configuredTop)
      ? Math.max(configuredTop, fullUniverseTop)
      : fullUniverseTop;
    return { ...merged, top: String(top) };
  }, [dashboardConfig, market, symbols.length]);
  const signalThresholds = dashboardConfig?.signal_thresholds || {};
  const signalThresholdLabel = signalThresholds.label || "";
  const modelQualityConfig = dashboardConfig?.model_quality || {};
  const recUniverse = useMemo(() => symbols.map((s) => s.symbol).join(","), [symbols]);
  const universeIsLoading = universeSource === "loading";
  const universeIsFallback = universeSource === "fallback";
  const universeLabel = universeIsLoading ? "LOADING" : (universeIsFallback ? "FALLBACK" : "API");
  const effectiveRecSource = recSource;
  const recApiReady = effectiveRecSource === "api" && !universeIsLoading && recUniverse.length > 0;
  const advisorRequestEnabled = advisorEnabled;
  const cmrsSizingRequestEnabled = cmrsSizingEnabled;
  const recRequestParams = useMemo(() => {
    const params = {
      universe: recUniverse,
      ...recApiDefaults,
      output_dir: `reports/api_recommend_${market.toLowerCase()}`,
    };
    delete params.sizing_kind;
    delete params.sizing_alpha;
    delete params.sizing_n_min;
    if (cmrsSizingRequestEnabled) {
      const configuredKind = String(recApiDefaults.sizing_kind || "").trim();
      params.sizing_kind = configuredKind && configuredKind !== "off" ? configuredKind : "auto";
      params.sizing_alpha = String(recApiDefaults.sizing_alpha || "0.1");
      params.sizing_n_min = String(recApiDefaults.sizing_n_min || "30");
    }
    if (advisorRequestEnabled) {
      params.advisor_run = "1";
      params.advisor_blend_weight = "0.3";
    }
    return params;
  }, [advisorRequestEnabled, cmrsSizingRequestEnabled, market, recApiDefaults, recUniverse]);
  const recApiUrl = useMemo(() => {
    const params = new URLSearchParams(recRequestParams);
    return apiUrl(`/api/recommend?${params.toString()}`);
  }, [recRequestParams]);
  const recApiDefaultText = useMemo(
    () => Object.entries(recRequestParams)
      .filter(([key]) => !["universe", "output_dir"].includes(key))
      .map(([key, value]) => `${key}=${value}`)
      .join(" · "),
    [recRequestParams]
  );
  const pickSymbol = useCallback((symbol) => {
    setSelected(symbol);
  }, []);

  /* Executive layout — auto-fetch /api/recommend whenever selected ticker changes */
  useEffect(() => {
    if (!EXEC_LAYOUT || !selected) return;
    let cancelled = false;
    setExecSnapLoading(true);
    const mkt = selected.endsWith(".KS") || selected.endsWith(".KQ") ? "KRX" : "US";
    const params = new URLSearchParams({
      universe: selected,
      market: mkt,
      top: "1",
      period: "1y",
      data_provider: mkt === "KRX" ? "pykrx" : "yfinance",
      output_dir: `reports/exec_rec_${mkt.toLowerCase()}`,
    });
    fetch(`${API_BASE}/api/recommend?${params}`)
      .then(r => r.json())
      .then(data => {
        if (cancelled) return;
        const result = data?.results?.[0] ?? null;
        setExecSnap(result);
      })
      .catch(() => { if (!cancelled) setExecSnap(null); })
      .finally(() => { if (!cancelled) setExecSnapLoading(false); });
    return () => { cancelled = true; };
  }, [selected, EXEC_LAYOUT]);

  /* font + clock */
  useEffect(() => {
    const link = document.createElement("link");
    link.href =
      "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700&display=swap";
    link.rel = "stylesheet";
    document.head.appendChild(link);
    const tid = setInterval(() => {
      const d = new Date();
      const utc = d.toISOString().slice(11, 19);
      const ny = d.toLocaleTimeString("en-US", {
        timeZone: "America/New_York", hour12: false,
      });
      const kr = d.toLocaleTimeString("en-US", {
        timeZone: "Asia/Seoul", hour12: false,
      });
      setClock(`UTC ${utc}  ·  NYC ${ny}  ·  KST ${kr}`);
    }, 1000);
    return () => {
      clearInterval(tid);
      try { document.head.removeChild(link); } catch (e) {}
    };
  }, []);

  // KRX advisor restriction removed — has_live_advisor_key() gate on backend is sufficient

  /* runtime dashboard config */
  useEffect(() => {
    let cancelled = false;
    fetchDashboardConfig()
      .then((config) => {
        if (cancelled) return;
        setDashboardConfig(config);
        setDashboardConfigError("");
        setUniverseByMarket({
          US: config.markets.US.fallback_symbols,
          KRX: config.markets.KRX.fallback_symbols,
        });
      })
      .catch((e) => {
        if (cancelled) return;
        setDashboardConfigError(e.message || "dashboard config unavailable");
        setUniverseSource("fallback");
      });
    return () => { cancelled = true; };
  }, []);

  /* backend-owned universe */
  useEffect(() => {
    if (!dashboardConfig) return;
    let cancelled = false;
    setUniverseSource("loading");
    setUniverseError("");
    fetchUniverse(market)
      .then((payload) => {
        if (cancelled) return;
        setUniverseByMarket((current) => ({ ...current, [market]: payload.symbols }));
        setUniverseSource(payload.source || "backend_config");
        setUniverseError("");
      })
      .catch((e) => {
        if (cancelled) return;
        const fallback = fallbackSymbolsByMarket[market] || [];
        setUniverseByMarket((current) => ({ ...current, [market]: fallback }));
        setUniverseSource("fallback");
        setUniverseError(e.message || "universe API failed");
      });
    return () => { cancelled = true; };
  }, [market, dashboardConfig, fallbackSymbolsByMarket]);

  /* fetch on selection */
  useEffect(() => {
    if (!dashboardConfig) return;
    if (!selected) return;
    if (!symbolPeriod) return;
    if (cache[selected]) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    fetchSymbol(selected, symbolPeriod, symbolDataProvider).then((res) => {
      if (cancelled) return;
      if (res.error || !Array.isArray(res.data) || res.data.length < 30) {
        setSymbolErrors((current) => ({
          ...current,
          [selected]: res.error || "real provider returned insufficient OHLCV rows",
        }));
        setCache((c) => ({ ...c, [selected]: { ...res, fetchedAt: Date.now() } }));
        setLoading(false);
        return;
      }
      setSymbolErrors((current) => {
        const next = { ...current };
        delete next[selected];
        return next;
      });
      setCache((c) => ({ ...c, [selected]: { ...res, fetchedAt: Date.now() } }));
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [selected, cache, symbolPeriod, symbolDataProvider, dashboardConfig]);

  /* backend model evidence for primary SIGNAL/MODELS */
  const modelEvidenceCacheKey = `${selected}__lstm${lstmEnabled ? 1 : 0}`;
  useEffect(() => {
    if (!selected) return;
    if (Object.keys(modelScoreDefaults).length === 0) return;
    if (modelEvidenceCache[modelEvidenceCacheKey]) return;
    let cancelled = false;
    setModelEvidenceLoading(true);
    const params = { ...modelScoreDefaults };
    if (lstmEnabled) params.use_lstm = "1";
    fetchModelEvidence(selected, params)
      .then((payload) => {
        if (cancelled) return;
        setModelEvidenceCache((current) => ({ ...current, [modelEvidenceCacheKey]: payload }));
        setModelEvidenceErrors((current) => {
          const next = { ...current };
          delete next[modelEvidenceCacheKey];
          return next;
        });
      })
      .catch((e) => {
        if (cancelled) return;
        setModelEvidenceErrors((current) => ({
          ...current,
          [modelEvidenceCacheKey]: e.message || "MODEL EVIDENCE UNAVAILABLE",
        }));
      })
      .finally(() => {
        if (!cancelled) setModelEvidenceLoading(false);
      });
    return () => { cancelled = true; };
  }, [selected, modelEvidenceCache, modelScoreDefaults, lstmEnabled, modelEvidenceCacheKey]);

  /* paper-only trading status */
  useEffect(() => {
    if (tab !== "PAPER" || paperStatusLoading) return;
    let cancelled = false;
    setPaperStatusLoading(true);
    fetchPaperStatus()
      .then((payload) => {
        if (cancelled) return;
        setPaperStatus(payload);
        setPaperStatusError("");
      })
      .catch((e) => {
        if (cancelled) return;
        setPaperStatusError(e.message || "paper status API failed");
      })
      .finally(() => {
        if (!cancelled) setPaperStatusLoading(false);
      });
    return () => { cancelled = true; };
  }, [tab]);

  /* universe source controls the initial selected symbol */
  useEffect(() => {
    if (universeSource === "loading") return;
    const first = symbols[0]?.symbol;
    if (!first) return;
    const selectedIsValid = symbols.some((s) => s.symbol === selected);
    if (!selected || !selectedIsValid) {
      setSelected(first);
    }
    setBench({ open: false, rows: [], loading: false, progress: 0 });
  }, [market, selected, symbols, universeSource]);

  const cur = cache[selected];
  const enriched = useMemo(() => (cur ? enrich(cur.data) : []), [cur]);
  const lastIdx = enriched.length - 1;
  const last = lastIdx >= 0 ? enriched[lastIdx] : null;
  const prev = lastIdx > 0 ? enriched[lastIdx - 1] : null;
  const change = last && prev ? last.close - prev.close : 0;
  const changePct = last && prev ? (change / prev.close) * 100 : 0;

  const feat = useMemo(() => (last ? features(enriched, lastIdx) : null), [enriched, lastIdx, last]);
  const browserScores = useMemo(() => {
    if (!last) return null;
    return {
      lr: lrPredict(feat),
      xgb: xgbPredict(feat),
      lstm: lstmPredict(enriched, lastIdx),
      rnn: rnnPredict(enriched, lastIdx),
    };
  }, [feat, enriched, lastIdx, last]);
  const modelEvidence = modelEvidenceCache[modelEvidenceCacheKey] || null;
  const modelEvidenceError = modelEvidenceErrors[modelEvidenceCacheKey] || "";
  const scores = useMemo(() => scoresFromModelEvidence(modelEvidence), [modelEvidence]);
  const modelQualityWarning = useMemo(
    () => getModelQualityWarning(modelEvidence, modelQualityConfig),
    [modelEvidence, modelQualityConfig]
  );
  const ens = scores ? Number(modelEvidence.ensemble_score) : null;
  const sig = scores ? modelEvidence.signal : null;

  const backtest = useMemo(
    () => (enriched.length > 35 ? runBacktest(enriched, signalThresholds) : null),
    [enriched, signalThresholds]
  );

  /* prefetch other symbols' last-prices for sidebar */
  const [sidebarSnap, setSidebarSnap] = useState({});
  useEffect(() => {
    if (!dashboardConfig) return;
    if (universeSource === "loading") return;
    if (!symbolPeriod) return;
    let cancel = false;
    (async () => {
      for (const s of symbols) {
        if (cancel) return;
        if (sidebarSnap[s.symbol] || cache[s.symbol]) {
          if (cache[s.symbol]) {
            const en = enrich(cache[s.symbol].data);
            const l = en[en.length - 1];
            const p = en[en.length - 2];
            if (l && p) {
              setSidebarSnap((x) => ({
                ...x,
                [s.symbol]: { price: l.close, chg: ((l.close - p.close) / p.close) * 100, src: cache[s.symbol].source },
              }));
            }
          }
          continue;
        }
        const res = await fetchSymbol(s.symbol, symbolPeriod, symbolDataProvider);
        if (cancel) return;
        if (res.error || !Array.isArray(res.data) || res.data.length < 30) {
          setSidebarSnap((x) => ({
            ...x,
            [s.symbol]: { error: res.error || "real provider unavailable", src: "ERROR" },
          }));
          setCache((c) => ({ ...c, [s.symbol]: { ...res, fetchedAt: Date.now() } }));
          await new Promise((r) => setTimeout(r, 80));
          continue;
        }
        const en = enrich(res.data);
        const l = en[en.length - 1];
        const p = en[en.length - 2];
        setCache((c) => ({ ...c, [s.symbol]: { ...res, fetchedAt: Date.now() } }));
        if (l && p) {
          setSidebarSnap((x) => ({
            ...x,
            [s.symbol]: { price: l.close, chg: ((l.close - p.close) / p.close) * 100, src: res.source },
          }));
        }
        await new Promise((r) => setTimeout(r, 80));
      }
    })();
    return () => { cancel = true; };
    // eslint-disable-next-line
  }, [market, universeSource, symbols, symbolPeriod, symbolDataProvider, dashboardConfig]);

  /* benchmark scan */
  const runBenchmark = useCallback(async () => {
    if (!dashboardConfig) return;
    if (!symbolPeriod) return;
    setBench({ open: true, rows: [], loading: true, progress: 0 });
    const rows = [];
    let done = 0;
    for (const s of symbols) {
      let pkg = cache[s.symbol];
      if (!pkg) {
        pkg = await fetchSymbol(s.symbol, symbolPeriod, symbolDataProvider);
        setCache((c) => ({ ...c, [s.symbol]: { ...pkg, fetchedAt: Date.now() } }));
      }
      if (pkg.error || !Array.isArray(pkg.data) || pkg.data.length < 30) {
        done++;
        setBench((b) => ({ ...b, progress: done / symbols.length }));
        continue;
      }
      const en = enrich(pkg.data);
      const i = en.length - 1;
      if (i >= 30) {
        const f = features(en, i);
        const sc = {
          lr: lrPredict(f),
          xgb: xgbPredict(f),
          lstm: lstmPredict(en, i),
          rnn: rnnPredict(en, i),
        };
        const e = ensembleScore(sc);
        rows.push({
          symbol: s.symbol, name: s.name,
          price: en[i].close,
          chg: en[i - 1] ? ((en[i].close - en[i - 1].close) / en[i - 1].close) * 100 : 0,
          rsi: en[i].rsi, ...sc, ens: e, sig: signalFromScore(e, signalThresholds),
          src: pkg.source,
        });
      }
      done++;
      setBench((b) => ({ ...b, progress: done / symbols.length }));
    }
    rows.sort((a, b) => b.ens - a.ens);
    setBench({ open: true, rows, loading: false, progress: 1 });
  }, [cache, symbols, signalThresholds, symbolPeriod, symbolDataProvider, dashboardConfig]);

  /* export helpers */
  const fmtMoney = (v) =>
    market === "US"
      ? `$${v.toFixed(2)}`
      : `₩${Math.round(v).toLocaleString()}`;
  const fmtPct = (v) => `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;

  const triggerDownload = (text, name, mime) => {
    const blob = new Blob([text], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = name;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const exportJSON = () => {
    if (!cur || !last) return;
    const payload = {
      generated: new Date().toISOString(),
      app: "STOCK·PRED v5.0",
      market, symbol: selected,
      source: cur.source,
      lastBar: last,
      indicators: {
        rsi: last.rsi, macd: last.macd, macdSignal: last.macdSignal,
        macdHist: last.macdHist, bbUpper: last.bbUpper,
        bbMid: last.bbMid, bbLower: last.bbLower,
        ema12: last.ema12, ema26: last.ema26, ema50: last.ema50,
      },
      modelEvidence,
      browserDemoModels: browserScores,
      ensemble: ens, signal: sig,
      backtest: backtest && {
        initial: backtest.initial,
        finalVal: backtest.finalVal,
        bhFinal: backtest.bhFinal,
        mlReturnPct: backtest.mlRet * 100,
        bhReturnPct: backtest.bhRet * 100,
        alphaPct: backtest.alpha * 100,
        sharpe: backtest.sharpe,
        winRatePct: backtest.winRate * 100,
        totalTrades: backtest.totalTrades,
        completedTrades: backtest.completedTrades,
      },
    };
    triggerDownload(
      JSON.stringify(payload, null, 2),
      `stock-pred-${selected}-${Date.now()}.json`,
      "application/json"
    );
    setExportFlash("JSON ✓");
    setTimeout(() => setExportFlash(""), 1500);
  };

  const exportMD = () => {
    if (!cur || !last) return;
    const md = `# STOCK·PRED v5.0 — ${selected}
*Generated: ${new Date().toISOString()}*

## Market
- **Market:** ${market}
- **Symbol:** ${selected}
- **Data Source:** ${cur.source}
- **Last Close:** ${fmtMoney(last.close)} (${fmtPct(changePct)})

## Technical Indicators
| Indicator | Value |
|---|---|
| RSI(14) | ${last.rsi?.toFixed(2)} |
| MACD | ${last.macd?.toFixed(4)} |
| MACD Signal | ${last.macdSignal?.toFixed(4)} |
| MACD Hist | ${last.macdHist?.toFixed(4)} |
| BB Upper | ${last.bbUpper?.toFixed(2)} |
| BB Mid | ${last.bbMid?.toFixed(2)} |
| BB Lower | ${last.bbLower?.toFixed(2)} |
| EMA12 | ${last.ema12?.toFixed(2)} |
| EMA26 | ${last.ema26?.toFixed(2)} |

## Model Scores
${modelEvidence && scores ? `Backend model evidence: ${modelEvidence.model_kind} from ${modelEvidence.provider}, generated ${modelEvidence.evidence?.generated_at_utc || "unknown"}.

| Model | Score |
|---|---|
| Backend main | ${scores.main} |
| Logistic Regression | ${scores.lr ?? "N/A"} |
| XGBoost | ${scores.xgb ?? "N/A"} |
| LSTM | ${scores.lstm ?? "N/A"} |
| RNN | ${scores.rnn ?? "N/A"} |
| **Ensemble** | **${ens}** |` : "MODEL EVIDENCE UNAVAILABLE"}

## Signal: **${sig || "MODEL EVIDENCE UNAVAILABLE"}**

${backtest ? `## Backtest (\\$10,000 initial)
- Final ML: ${fmtMoney(backtest.finalVal)}
- Final B&H: ${fmtMoney(backtest.bhFinal)}
- ML Return: ${(backtest.mlRet * 100).toFixed(2)}%
- B&H Return: ${(backtest.bhRet * 100).toFixed(2)}%
- **Alpha: ${(backtest.alpha * 100).toFixed(2)}%**
- Sharpe: ${backtest.sharpe.toFixed(2)}
- Win Rate: ${(backtest.winRate * 100).toFixed(1)}%
- Trades: ${backtest.totalTrades} (completed: ${backtest.completedTrades})` : ""}
`;
    triggerDownload(md, `stock-pred-${selected}-${Date.now()}.md`, "text/markdown");
    setExportFlash("MD ✓");
    setTimeout(() => setExportFlash(""), 1500);
  };

  /* ======== chart-ready slices ======== */
  const chartSlice = useMemo(() => enriched.slice(-90), [enriched]);

  const sigColor = sig === "BUY" ? C.buy : sig === "SELL" ? C.sell : C.hold;
  const opsEvidence = useMemo(() => {
    const providerLabel = String(symbolDataProvider || "auto").toUpperCase();
    const evidenceLabel = modelEvidenceLoading
      ? "LOADING"
      : modelEvidence
        ? "LOCKED"
        : "WAITING";
    const evidenceColor = modelEvidence ? C.green : modelEvidenceLoading ? C.amber : C.red;
    return [
      {
        label: "DATA ROUTE",
        value: providerLabel,
        color: market === "KRX" ? C.krx : C.us,
        note: universeLabel,
      },
      {
        label: "MODEL EVIDENCE",
        value: evidenceLabel,
        color: evidenceColor,
        note: modelEvidenceError ? "backend check required" : "primary signal source",
      },
      {
        label: "REC MODE",
        value: recSource === "api" ? "API LIVE" : "FILE STATIC",
        color: recSource === "api" ? C.green : C.amber,
        note: recSource === "api" ? "recommendation endpoint" : "snapshot only",
      },
      {
        label: "EXECUTION",
        value: "REPORT ONLY",
        color: C.amber,
        note: "no new capital or broker orders",
      },
    ];
  }, [
    market,
    symbolDataProvider,
    universeLabel,
    modelEvidenceLoading,
    modelEvidence,
    modelEvidenceError,
    recSource,
  ]);

  /* ======================== RENDER ======================== */

  // ── Executive Decision Dashboard v2.1 ───────────────────────────────
  if (EXEC_LAYOUT) {
    const execSymbols = symbols.map(s => ({
      symbol: s.symbol, name: s.name || s.symbol,
      price: cache[s.symbol]?.data?.slice(-1)[0]?.close,
      change: null, changePct: null,
    }));
    // execSnap is auto-fetched via useEffect above; null until first load
    const snap = execSnap;
    const last = cache[selected]?.data?.slice(-1)[0];
    const prev = cache[selected]?.data?.slice(-2)[0];
    const chg = last && prev ? last.close - prev.close : null;
    const chgPct = prev && prev.close ? chg / prev.close * 100 : null;
    const scenario = snap?.scenario_outlook ?? null;
    const headlines = snap?.notebook_analysis
      ? (snap?.notebooklm_source_count ? [{ title: snap.notebook_analysis.summary || "NotebookLM analysis loaded", source: "NotebookLM", published_at: snap?.notebooklm_as_of }] : [])
      : [];

    return (
      <div style={{minHeight:"100vh",padding:22,background:"#020916",color:"#d4e1ec",fontFamily:`"Inter","JetBrains Mono",sans-serif`,boxSizing:"border-box"}}>
        <HeaderBar market={market} onMarketChange={setMarket} ticker={selected} onTickerChange={setSelected} symbols={execSymbols} accent={accent}/>
        {/* Loading banner */}
        {execSnapLoading && (
          <div style={{padding:"6px 12px",marginBottom:10,background:"rgba(32,214,210,0.07)",border:"1px solid rgba(32,214,210,0.2)",borderRadius:4,fontSize:10,color:"#20d6d2",letterSpacing:"0.05em"}}>
            ⟳ Loading AI analysis for {selected}…
          </div>
        )}
        {/* Top KPI row */}
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 0.95fr 1.45fr",gap:16,marginBottom:14}}>
          <CurrentPriceCard price={last?.close} change={chg} changePct={chgPct} volume={last?.volume} currency={currency}/>
          <RecommendationKpi verdict={snap?.verdict} advisorScore={snap?.advisor_score}/>
          <ConfidenceKpi confidence={snap?.notebooklm_confidence ?? snap?.probability}/>
          <RiskRewardKpi riskReward={snap?.risk_reward}/>
        </div>
        {/* Main decision grid */}
        <div style={{display:"grid",gridTemplateColumns:"0.95fr 1.9fr 2.85fr",gap:14,marginBottom:14,minHeight:448}}>
          <MarketSnapshotPanel result={snap}/>
          <div style={{display:"grid",gridTemplateRows:"1fr 160px",gap:12}}>
            <CompactPriceChart ohlcvRecords={cache[selected]?.data||[]} currency={currency}/>
            <ModelScoresPanel modelEvidence={modelEvidenceCache[modelEvidenceCacheKey]}/>
          </div>
          <AiDecisionPanel result={snap}/>
        </div>
        {/* Bottom insight grid */}
        <div style={{display:"grid",gridTemplateColumns:"1.35fr 1.45fr 2.2fr",gap:14,minHeight:220}}>
          <WatchlistPanel symbols={execSymbols} selected={selected} onSelect={setSelected}/>
          <NewsTimelinePanel headlines={headlines}/>
          <ScenarioOutlookPanel scenario={scenario}/>
        </div>
        <div style={{marginTop:10,fontSize:9,color:"#536476",textAlign:"center"}}>
          dashboard_snapshot.v1 · screening_output_only · Report-only · Manual review required · No broker execution
        </div>
      </div>
    );
  }
  // ── End Executive Layout ──────────────────────────────────────────────

  return (
    <div
      style={{
        background: C.bg,
        color: C.text,
        fontFamily: FONT,
        minHeight: "100vh",
        fontSize: 12,
      }}
      className="w-full"
    >
      {/* scanline overlay */}
      <div
        style={{
          position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0,
          background:
            "repeating-linear-gradient(0deg, rgba(0,204,255,0.018) 0px, rgba(0,204,255,0.018) 1px, transparent 1px, transparent 3px)",
        }}
      />

      {/* HEADER */}
      <header
        style={{
          borderBottom: `1px solid ${C.border}`,
          background: `linear-gradient(180deg, ${C.bgDeep} 0%, ${C.panel} 100%)`,
          position: "relative", zIndex: 1,
        }}
        className="px-4 py-3"
      >
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div
                style={{
                  width: 10, height: 10, borderRadius: 2, background: accent,
                  boxShadow: `0 0 12px ${accent}`,
                }}
              />
              <span style={{ color: accent, fontWeight: 700, letterSpacing: 2, fontSize: 14 }}>
                STOCK·PRED
              </span>
              <span style={{ color: C.textDim, fontSize: 10, letterSpacing: 1 }}>v5.0</span>
            </div>
            <div style={{ color: C.textMuted, fontSize: 10 }}>
              BACKEND MODEL EVIDENCE · DUAL MARKET · REPORT-ONLY
            </div>
          </div>

          {/* market toggle */}
          <div
            style={{
              display: "flex", border: `1px solid ${C.border}`, borderRadius: 4, overflow: "hidden",
            }}
          >
            <button
              onClick={() => setMarket("US")}
              style={{
                padding: "6px 16px",
                background: market === "US" ? C.us : "transparent",
                color: market === "US" ? "#001018" : C.textDim,
                fontWeight: 700, letterSpacing: 1.5, fontSize: 11,
                border: "none", cursor: "pointer",
                transition: "all .2s",
              }}
            >
              US
            </button>
            <button
              onClick={() => setMarket("KRX")}
              style={{
                padding: "6px 16px",
                background: market === "KRX" ? C.krx : "transparent",
                color: market === "KRX" ? "#150300" : C.textDim,
                fontWeight: 700, letterSpacing: 1.5, fontSize: 11,
                border: "none", cursor: "pointer",
                transition: "all .2s",
              }}
            >
              KRX
            </button>
          </div>

          <div style={{ color: C.textDim, fontSize: 10, letterSpacing: 1 }}>{clock}</div>

          <div className="flex items-center gap-2">
            <button
              onClick={runBenchmark}
              style={{
                padding: "6px 12px", background: "transparent",
                border: `1px solid ${accent}`, color: accent,
                fontFamily: FONT, fontSize: 10, letterSpacing: 1.5, fontWeight: 600,
                cursor: "pointer",
              }}
            >
              ◊ BENCHMARK
            </button>
            <button
              onClick={exportJSON}
              style={{
                padding: "6px 10px", background: "transparent",
                border: `1px solid ${C.border}`, color: C.textDim,
                fontFamily: FONT, fontSize: 10, letterSpacing: 1.5,
                cursor: "pointer",
              }}
            >
              JSON
            </button>
            <button
              onClick={exportMD}
              style={{
                padding: "6px 10px", background: "transparent",
                border: `1px solid ${C.border}`, color: C.textDim,
                fontFamily: FONT, fontSize: 10, letterSpacing: 1.5,
                cursor: "pointer",
              }}
            >
              MD
            </button>
            {exportFlash && (
              <span style={{ color: C.green, fontSize: 10, letterSpacing: 1 }}>{exportFlash}</span>
            )}
          </div>
        </div>
      </header>

      <OperationalEvidenceStrip items={opsEvidence} accent={accent} selected={selected} />

      {/* MAIN */}
      <div
        style={{ position: "relative", zIndex: 1 }}
        className="grid"
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "220px 1fr 360px",
            minHeight: "calc(100vh - 56px)",
          }}
        >
          {/* LEFT: SYMBOLS */}
          <aside
            style={{
              borderRight: `1px solid ${C.border}`,
              background: C.panel,
              padding: 8, overflowY: "auto",
            }}
          >
            <div
              style={{
                padding: "8px 10px 10px",
                borderBottom: `1px solid ${C.borderSoft}`,
                marginBottom: 4,
              }}
            >
              <div style={{
                fontFamily: FONT_SANS,
                color: C.textLabel, fontSize: 10, fontWeight: 600,
                letterSpacing: "0.08em", textTransform: "uppercase",
                display: "flex", alignItems: "center", gap: 6,
              }}>
                <span style={{ width: 3, height: 10, background: C.us, borderRadius: 2, display: "inline-block" }} />
                SYMBOLS · {market}
              </div>
              <div style={{ marginTop: 4, color: universeIsFallback ? C.amber : C.green, fontSize: 8, fontFamily: FONT, letterSpacing: 1 }}>
                UNIVERSE: {universeLabel}
                {universeError ? ` · ${universeError}` : ""}
              </div>
            </div>
            {symbols.map((s) => {
              const snap = sidebarSnap[s.symbol];
              const isActive = s.symbol === selected;
              return (
                <button
                  key={s.symbol}
                  onClick={() => pickSymbol(s.symbol)}
                  style={{
                    width: "100%", textAlign: "left",
                    padding: "8px 10px", marginBottom: 3,
                    background: isActive ? C.panelHi : "transparent",
                    borderLeft: `2px solid ${isActive ? accent : "transparent"}`,
                    borderTop: "none", borderRight: "none", borderBottom: "none",
                    cursor: "pointer",
                    fontFamily: FONT, color: C.text,
                    transition: "background .15s",
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive) e.currentTarget.style.background = C.panel2;
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) e.currentTarget.style.background = "transparent";
                  }}
                >
                  <div className="flex justify-between items-baseline">
                    <span
                      style={{
                        fontWeight: 600, fontSize: 11,
                        color: isActive ? accent : C.text,
                      }}
                    >
                      {s.symbol.replace(".KS", "")}
                    </span>
                    {snap && !snap.error && (
                      <span
                        style={{
                          fontSize: 10,
                          color: snap.chg >= 0 ? C.green : C.red,
                        }}
                      >
                        {snap.chg >= 0 ? "▲" : "▼"} {Math.abs(snap.chg).toFixed(2)}%
                      </span>
                    )}
                  </div>
                  <div className="flex justify-between mt-0.5">
                    <span style={{ fontSize: 9, color: C.textDim }}>{s.name}</span>
                    {snap && !snap.error && (
                      <span style={{ fontSize: 9, color: C.textDim }}>
                        {market === "US"
                          ? `$${snap.price.toFixed(2)}`
                          : `₩${Math.round(snap.price).toLocaleString()}`}
                      </span>
                    )}
                  </div>
                  {snap?.error && (
                    <div style={{ fontSize: 8, color: C.red, letterSpacing: 1 }}>DATA ERROR</div>
                  )}
                </button>
              );
            })}
            <div
              style={{
                marginTop: 12, padding: 8, borderTop: `1px solid ${C.border}`,
                fontSize: 9, color: C.textMuted, letterSpacing: 1, lineHeight: 1.5,
              }}
            >
              <div>{signalThresholdLabel}</div>
              <div style={{ marginTop: 4 }}>
                SIGNAL/MODELS = BACKEND MODEL EVIDENCE
              </div>
              {dashboardConfigError && (
                <div style={{ marginTop: 4, color: C.red }}>
                  CONFIG: {dashboardConfigError}
                </div>
              )}
            </div>
          </aside>

          {/* CENTER */}
          <main style={{ padding: 12, overflow: "auto" }}>
            {bench.open ? (
              <BenchmarkPanel
                bench={bench}
                accent={accent}
                market={market}
                onClose={() => setBench({ open: false, rows: [], loading: false, progress: 0 })}
                onPick={(sym) => {
                  pickSymbol(sym);
                  setBench({ open: false, rows: [], loading: false, progress: 0 });
                }}
              />
            ) : (
              <CenterPanel
                cur={cur}
                loading={loading}
                last={last}
                prev={prev}
                change={change}
                changePct={changePct}
                chartSlice={chartSlice}
                accent={accent}
                market={market}
                selected={selected}
                symbolName={symbols.find((s) => s.symbol === selected)?.name || ""}
                fmtMoney={fmtMoney}
                error={symbolErrors[selected] || cur?.error || ""}
              />
            )}
          </main>

          {/* RIGHT */}
          <aside
            style={{
              borderLeft: `1px solid ${C.border}`,
              background: C.panel, overflow: "auto",
            }}
          >
            <div
              style={{
                display: "flex", borderBottom: `1px solid ${C.border}`, background: C.bgDeep,
              }}
            >
              {["SIGNAL", "MODELS", "BACKTEST", "REC", "PAPER"].map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  style={{
                    flex: 1, padding: "10px 0",
                    background: tab === t ? `${accent}12` : "transparent",
                    border: "none",
                    borderBottom: `2px solid ${tab === t ? accent : "transparent"}`,
                    color: tab === t ? accent : C.textDim,
                    fontFamily: FONT_SANS, fontWeight: tab === t ? 700 : 500,
                    letterSpacing: "0.06em", fontSize: 10,
                    cursor: "pointer", transition: "all .15s",
                    boxShadow: tab === t ? `inset 0 -1px 0 ${accent}` : "none",
                  }}
                >
                  {t}
                </button>
              ))}
            </div>

            <div style={{ padding: "14px 16px" }}>
              {tab === "SIGNAL" && (
                <SignalTab
                  last={last}
                  scores={scores}
                  ens={ens}
                  sig={sig}
                  sigColor={sigColor}
                  feat={feat}
                  accent={accent}
                  modelEvidence={modelEvidence}
                  modelEvidenceError={modelEvidenceError}
                  modelEvidenceLoading={modelEvidenceLoading}
                  modelQualityWarning={modelQualityWarning}
                  signalThresholdLabel={signalThresholdLabel}
                  signalThresholds={signalThresholds}
                />
              )}
              {tab === "MODELS" && (
                <ModelsTab
                  scores={scores}
                  ens={ens}
                  sig={sig}
                  sigColor={sigColor}
                  modelEvidence={modelEvidence}
                  modelEvidenceError={modelEvidenceError}
                  modelEvidenceLoading={modelEvidenceLoading}
                  modelQualityWarning={modelQualityWarning}
                  signalThresholds={signalThresholds}
                />
              )}
              {tab === "BACKTEST" && (
                <BacktestTab
                  backtest={backtest}
                  market={market}
                  fmtMoney={fmtMoney}
                  accent={accent}
                />
              )}
              {tab === "REC" && (
                <div>
                  {/* Source toggle */}
                  <div style={{ display: "flex", gap: 4, padding: "6px 8px", borderBottom: `1px solid ${C.border}` }}>
                    {[
                      { k: "file", l: "FILE" },
                      { k: "api", l: "API" },
                    ].map((s) => (
                      <button
                        key={s.k}
                        onClick={() => setRecSource(s.k)}
                        style={{
                          flex: 1, padding: "4px 0",
                          background: effectiveRecSource === s.k ? C.panelHi : "transparent",
                          border: `1px solid ${effectiveRecSource === s.k ? accent : C.border}`,
                          color: effectiveRecSource === s.k ? accent : C.textMuted,
                          opacity: 1,
                          fontFamily: FONT, fontSize: 8, letterSpacing: 1.5, fontWeight: 600,
                          cursor: "pointer",
                        }}
                      >
                        {s.l}
                      </button>
                    ))}
                  </div>
                  {effectiveRecSource === "api" && (
                    <div style={{
                      margin: "8px 8px 0",
                      padding: "6px 8px",
                      border: `1px solid ${C.border}`,
                      color: C.textDim,
                      background: C.bgDeep,
                      fontFamily: FONT,
                      fontSize: 8,
                      letterSpacing: 1,
                      lineHeight: 1.5,
                    }}>
                      <span style={{ color: accent, fontWeight: 700 }}>API REQUEST DEFAULTS</span>
                      <span> · {recApiDefaultText}</span>
                    </div>
                  )}
                  {effectiveRecSource === "api" && (
                    <div style={{
                      margin: "4px 8px 0",
                      padding: "5px 8px",
                      border: `1px solid ${advisorEnabled ? "#BB66FF55" : C.border}`,
                      background: advisorEnabled ? "#0D0A1A" : C.bgDeep,
                      fontFamily: FONT,
                      fontSize: 8,
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      cursor: "pointer",
                      userSelect: "none",
                    }}
                      onClick={() => {
                        setAdvisorEnabled((v) => !v);
                      }}
                    >
                      <div style={{
                        width: 24, height: 12, borderRadius: 6,
                        background: advisorRequestEnabled ? "#BB66FF" : C.border,
                        position: "relative", transition: "background .15s", flexShrink: 0,
                      }}>
                        <div style={{
                          position: "absolute", top: 2,
                          left: advisorRequestEnabled ? 14 : 2,
                          width: 8, height: 8, borderRadius: "50%",
                          background: "#fff", transition: "left .15s",
                        }} />
                      </div>
                      <span style={{ color: advisorRequestEnabled ? "#BB66FF" : C.textMuted, fontWeight: 600, letterSpacing: 1.5 }}>
                        LLM ADVISOR
                      </span>
                      <span style={{ color: C.textMuted, marginLeft: "auto" }}>
                        {advisorRequestEnabled
                          ? "blend_weight=0.30 · requires ANTHROPIC_API_KEY or MINIMAX_API_KEY"
                          : "OFF"}
                      </span>
                    </div>
                  )}
                  {effectiveRecSource === "api" && (
                    <div style={{
                      margin: "4px 8px 0",
                      padding: "5px 8px",
                      border: `1px solid ${cmrsSizingEnabled ? `${C.green}55` : C.border}`,
                      background: cmrsSizingEnabled ? "#07150F" : C.bgDeep,
                      fontFamily: FONT,
                      fontSize: 8,
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      cursor: "pointer",
                      userSelect: "none",
                    }}
                      onClick={() => setCmrsSizingEnabled((v) => !v)}
                    >
                      <div style={{
                        width: 24, height: 12, borderRadius: 6,
                        background: cmrsSizingRequestEnabled ? C.green : C.border,
                        position: "relative", transition: "background .15s", flexShrink: 0,
                      }}>
                        <div style={{
                          position: "absolute", top: 2,
                          left: cmrsSizingRequestEnabled ? 14 : 2,
                          width: 8, height: 8, borderRadius: "50%",
                          background: "#fff", transition: "left .15s",
                        }} />
                      </div>
                      <span style={{ color: cmrsSizingRequestEnabled ? C.green : C.textMuted, fontWeight: 600, letterSpacing: 1.5 }}>
                        CMRS SIZING
                      </span>
                      <span style={{ color: C.textMuted, marginLeft: "auto" }}>
                        {cmrsSizingRequestEnabled
                          ? `sizing_kind=${recRequestParams.sizing_kind} · alpha=${recRequestParams.sizing_alpha} · n_min=${recRequestParams.sizing_n_min}`
                          : "OFF"}
                      </span>
                    </div>
                  )}
                  {/* LSTM toggle — activates use_lstm=1 on /api/model-scores */}
                  <div style={{
                    margin: "4px 8px 0",
                    padding: "5px 8px",
                    border: `1px solid ${lstmEnabled ? "#BB66FF55" : C.border}`,
                    background: lstmEnabled ? "#0A0D1A" : C.bgDeep,
                    fontFamily: FONT,
                    fontSize: 8,
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    cursor: "pointer",
                    userSelect: "none",
                  }}
                    onClick={() => setLstmEnabled((v) => !v)}
                  >
                    <div style={{
                      width: 24, height: 12, borderRadius: 6,
                      background: lstmEnabled ? C.lstm : C.border,
                      position: "relative", transition: "background .15s", flexShrink: 0,
                    }}>
                      <div style={{
                        position: "absolute", top: 2,
                        left: lstmEnabled ? 14 : 2,
                        width: 8, height: 8, borderRadius: "50%",
                        background: "#fff", transition: "left .15s",
                      }} />
                    </div>
                    <span style={{ color: lstmEnabled ? C.lstm : C.textMuted, fontWeight: 600, letterSpacing: 1.5 }}>
                      LSTM
                    </span>
                    <span style={{ color: C.textMuted, marginLeft: "auto" }}>
                      {lstmEnabled ? "use_lstm=1 · PyTorch GPU · re-fetches scores" : "OFF"}
                    </span>
                  </div>
                  {effectiveRecSource === "file" && (
                    <div style={{
                      margin: "8px 8px 0",
                      padding: "6px 8px",
                      border: `1px solid ${C.amber}`,
                      color: C.amber,
                      background: C.bgDeep,
                      fontFamily: FONT,
                      fontSize: 8,
                      letterSpacing: 1,
                      lineHeight: 1.5,
                    }}>
                      STATIC SNAPSHOT · FILE mode reads saved public JSON. It is not live market data.
                    </div>
                  )}
                  {effectiveRecSource === "api" && !recApiReady ? (
                    <div style={{ padding: 12, color: C.textDim, fontSize: 10 }}>
                      REC API is waiting for `/api/universe` before requesting recommendations.
                    </div>
                  ) : (
                    <RecommendationPanel
                      key={`${market}-${effectiveRecSource}-${recUniverse}`}
                      jsonPath={effectiveRecSource === "file" ? "/dashboard_snapshot.json" : null}
                      apiUrl={effectiveRecSource === "api" ? recApiUrl : null}
                      currency={currency}
                      accent={accent}
                    />
                  )}
                </div>
              )}
              {tab === "PAPER" && (
                <PaperTradingTab
                  status={paperStatus}
                  loading={paperStatusLoading}
                  error={paperStatusError}
                  accent={accent}
                  fmtMoney={fmtMoney}
                />
              )}
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

/* ====================  SUB-PANELS  ==================== */

function CenterPanel({
  cur, loading, last, prev, change, changePct, chartSlice, accent,
  market, selected, symbolName, fmtMoney,
  error,
}) {
  if (error) {
    const isNetworkError = /failed to fetch|abort|network|request failed/i.test(String(error));
    const failureReason = isNetworkError
      ? "the backend API could not be reached."
      : "the backend/provider did not return enough OHLCV rows.";
    return (
      <div
        style={{
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          height: "100%", color: C.amber, fontSize: 12, letterSpacing: 1.5, textAlign: "center", padding: 24,
        }}
      >
        <div style={{ color: C.red, fontWeight: 700, marginBottom: 8 }}>REAL DATA LOAD FAILED</div>
        <div style={{ maxWidth: 520, lineHeight: 1.7 }}>
          {selected} chart data was not rendered because {failureReason}
        </div>
        <div style={{ marginTop: 8, color: C.textDim, fontSize: 10 }}>{error}</div>
      </div>
    );
  }

  if (loading || !cur || !last) {
    return (
      <div
        style={{
          display: "flex", alignItems: "center", justifyContent: "center",
          height: "100%", color: C.textDim, fontSize: 14, letterSpacing: 2,
        }}
      >
        ◌ FETCHING {selected} ...
      </div>
    );
  }

  const upPct = ((last.bbUpper - last.bbLower) / last.bbMid) * 100;

  return (
    <>
      {/* TITLE STRIP */}
      <div
        style={{
          display: "flex", alignItems: "center", gap: 10, marginBottom: 14,
          paddingBottom: 12, borderBottom: `1px solid ${C.border}`,
          flexWrap: "wrap",
        }}
      >
        {/* Ticker + name */}
        <div>
          <div style={{ fontSize: 26, fontWeight: 800, color: accent, letterSpacing: 3, lineHeight: 1 }}>
            {selected.replace(".KS", "")}
          </div>
          <div style={{ color: C.textDim, fontSize: 10, fontFamily: FONT_SANS, marginTop: 2, letterSpacing: "0.05em" }}>
            {symbolName}
          </div>
        </div>

        {/* Divider */}
        <div style={{ width: 1, height: 32, background: C.border, margin: "0 6px" }} />

        {/* Price */}
        <div>
          <div style={{ fontSize: 30, fontWeight: 700, color: C.text, letterSpacing: 1, lineHeight: 1 }}>
            {fmtMoney(last.close)}
          </div>
          <div
            style={{
              color: change >= 0 ? C.green : C.red,
              fontSize: 11, fontWeight: 600, marginTop: 3,
              fontFamily: FONT_SANS,
            }}
          >
            {change >= 0 ? "▲" : "▼"} {Math.abs(change).toFixed(market === "US" ? 2 : 0)}{" "}
            ({changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%)
          </div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <Badge label="SRC" value={cur.source} color={cur.source === "YAHOO" || cur.source === "YFINANCE" ? C.green : C.amber} />
          <Badge label="O" value={fmtMoney(last.open)} color={C.textDim} />
          <Badge label="H" value={fmtMoney(last.high)} color={C.green} />
          <Badge label="L" value={fmtMoney(last.low)} color={C.red} />
          <Badge label="VOL" value={(last.volume / 1e6).toFixed(2) + "M"} color={C.textDim} />
        </div>
      </div>

      {/* PRICE + BB */}
      <Panel title="PRICE · EMA · BOLLINGER 20·2" right={`Width ${upPct.toFixed(2)}%`}>
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={chartSlice} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid stroke={C.grid} strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: C.textDim, fontSize: 9, fontFamily: FONT }} stroke={C.border} interval="preserveStartEnd" minTickGap={40} />
            <YAxis domain={["auto", "auto"]} tick={{ fill: C.textDim, fontSize: 9, fontFamily: FONT }} stroke={C.border} width={70} tickFormatter={(v) => market === "US" ? v.toFixed(0) : Math.round(v).toLocaleString()} />
            <Tooltip
              contentStyle={{
                background: C.bgDeep, border: `1px solid ${accent}`,
                fontFamily: FONT, fontSize: 11, color: C.text,
              }}
              labelStyle={{ color: accent }}
              formatter={(v) => (typeof v === "number" ? (market === "US" ? v.toFixed(2) : Math.round(v).toLocaleString()) : v)}
            />
            <Line type="monotone" dataKey="bbUpper" stroke={C.lstm} strokeWidth={1} dot={false} strokeDasharray="3 3" name="BB Upper" />
            <Line type="monotone" dataKey="bbMid" stroke={C.textMuted} strokeWidth={1} dot={false} strokeDasharray="2 2" name="BB Mid" />
            <Line type="monotone" dataKey="bbLower" stroke={C.lstm} strokeWidth={1} dot={false} strokeDasharray="3 3" name="BB Lower" />
            <Line type="monotone" dataKey="ema12" stroke={C.lr} strokeWidth={1.2} dot={false} name="EMA12" />
            <Line type="monotone" dataKey="ema26" stroke={C.xgb} strokeWidth={1.2} dot={false} name="EMA26" />
            <Line type="monotone" dataKey="close" stroke={accent} strokeWidth={2} dot={false} name="Close" />
          </ComposedChart>
        </ResponsiveContainer>
      </Panel>

      {/* RSI */}
      <Panel title="RSI · 14" right={`${last.rsi?.toFixed(2)}`} rightColor={last.rsi > 70 ? C.red : last.rsi < 30 ? C.green : C.textDim}>
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={chartSlice} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid stroke={C.grid} strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: C.textDim, fontSize: 9, fontFamily: FONT }} stroke={C.border} interval="preserveStartEnd" minTickGap={40} />
            <YAxis domain={[0, 100]} ticks={[0, 30, 50, 70, 100]} tick={{ fill: C.textDim, fontSize: 9, fontFamily: FONT }} stroke={C.border} width={36} />
            <Tooltip
              contentStyle={{
                background: C.bgDeep, border: `1px solid ${accent}`,
                fontFamily: FONT, fontSize: 11, color: C.text,
              }}
              labelStyle={{ color: accent }}
              formatter={(v) => (typeof v === "number" ? v.toFixed(2) : v)}
            />
            <ReferenceLine y={70} stroke={C.red} strokeDasharray="3 3" />
            <ReferenceLine y={30} stroke={C.green} strokeDasharray="3 3" />
            <ReferenceLine y={50} stroke={C.textMuted} strokeDasharray="1 3" />
            <Line type="monotone" dataKey="rsi" stroke={accent} strokeWidth={1.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </Panel>

      {/* MACD */}
      <Panel title="MACD · 12·26·9" right={`${last.macd?.toFixed(3)} / ${last.macdSignal?.toFixed(3)}`} rightColor={last.macdHist >= 0 ? C.green : C.red}>
        <ResponsiveContainer width="100%" height={120}>
          <ComposedChart data={chartSlice} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid stroke={C.grid} strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: C.textDim, fontSize: 9, fontFamily: FONT }} stroke={C.border} interval="preserveStartEnd" minTickGap={40} />
            <YAxis tick={{ fill: C.textDim, fontSize: 9, fontFamily: FONT }} stroke={C.border} width={50} tickFormatter={(v) => v.toFixed(1)} />
            <Tooltip
              contentStyle={{
                background: C.bgDeep, border: `1px solid ${accent}`,
                fontFamily: FONT, fontSize: 11, color: C.text,
              }}
              labelStyle={{ color: accent }}
              formatter={(v) => (typeof v === "number" ? v.toFixed(3) : v)}
            />
            <ReferenceLine y={0} stroke={C.textMuted} />
            <Bar dataKey="macdHist" name="Hist" fill={C.amber}>
              {chartSlice.map((d, i) => (
                <rect key={i} fill={d.macdHist >= 0 ? C.green : C.red} fillOpacity={0.55} />
              ))}
            </Bar>
            <Line type="monotone" dataKey="macd" stroke={C.lr} strokeWidth={1.4} dot={false} />
            <Line type="monotone" dataKey="macdSignal" stroke={C.rnn} strokeWidth={1.4} dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </Panel>

      {/* VOLUME */}
      <Panel title="VOLUME">
        <ResponsiveContainer width="100%" height={80}>
          <BarChart data={chartSlice} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid stroke={C.grid} strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: C.textDim, fontSize: 9, fontFamily: FONT }} stroke={C.border} interval="preserveStartEnd" minTickGap={40} />
            <YAxis tick={{ fill: C.textDim, fontSize: 9, fontFamily: FONT }} stroke={C.border} width={50} tickFormatter={(v) => v >= 1e6 ? (v / 1e6).toFixed(1) + "M" : v >= 1e3 ? (v / 1e3).toFixed(0) + "K" : v} />
            <Tooltip
              contentStyle={{
                background: C.bgDeep, border: `1px solid ${accent}`,
                fontFamily: FONT, fontSize: 11, color: C.text,
              }}
              labelStyle={{ color: accent }}
              formatter={(v) => v.toLocaleString()}
            />
            <Bar dataKey="volume" fill={accent} fillOpacity={0.55} />
          </BarChart>
        </ResponsiveContainer>
      </Panel>
    </>
  );
}

function OperationalEvidenceStrip({ items, accent, selected }) {
  return (
    <div
      style={{
        position: "relative",
        zIndex: 1,
        display: "grid",
        gridTemplateColumns: "minmax(150px, 0.72fr) repeat(4, minmax(150px, 1fr))",
        gap: 8,
        padding: "8px 12px",
        background: C.bgDeep,
        borderBottom: `1px solid ${C.borderSoft}`,
      }}
    >
      <div
        style={{
          minWidth: 0,
          padding: "7px 9px",
          background: C.panel,
          border: `1px solid ${accent}55`,
          borderLeft: `3px solid ${accent}`,
        }}
      >
        <div style={{ color: C.textMuted, fontSize: 8, letterSpacing: 1.4, fontFamily: FONT_SANS }}>
          ACTIVE SYMBOL
        </div>
        <div style={{ color: accent, fontSize: 13, fontWeight: 800, letterSpacing: "0.08em", marginTop: 2 }}>
          {selected || "N/A"}
        </div>
      </div>
      {items.map((item) => (
        <div
          key={item.label}
          style={{
            minWidth: 0,
            padding: "7px 9px",
            background: C.panel,
            border: `1px solid ${C.border}`,
            borderTop: `2px solid ${item.color}`,
            boxShadow: C.shadowSm,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              justifyContent: "space-between",
              gap: 8,
            }}
          >
            <span style={{ color: C.textMuted, fontSize: 8, letterSpacing: 1.2, fontFamily: FONT_SANS }}>
              {item.label}
            </span>
            <span style={{ color: item.color, fontSize: 11, fontWeight: 800, letterSpacing: "0.05em" }}>
              {item.value}
            </span>
          </div>
          <div
            style={{
              color: C.textDim,
              fontSize: 8,
              lineHeight: 1.35,
              marginTop: 3,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
            title={item.note}
          >
            {item.note}
          </div>
        </div>
      ))}
    </div>
  );
}

function Badge({ label, value, color }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1 }}>
      <span style={{ fontSize: 8, color: C.textMuted, letterSpacing: 1.5 }}>{label}</span>
      <span style={{ fontSize: 11, color: color || C.text, fontWeight: 500 }}>{value}</span>
    </div>
  );
}

function Panel({ title, right, rightColor, children }) {
  return (
    <div
      style={{
        background: C.panel,
        border: `1px solid ${C.border}`,
        marginBottom: 10,
      }}
    >
      <div
        style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "5px 10px", background: C.bgDeep,
          borderBottom: `1px solid ${C.border}`,
        }}
      >
        <span style={{ fontSize: 9, letterSpacing: 2, color: C.textDim, fontWeight: 600 }}>
          ▸ {title}
        </span>
        {right && (
          <span style={{ fontSize: 10, color: rightColor || C.text, fontWeight: 500 }}>
            {right}
          </span>
        )}
      </div>
      <div style={{ padding: 4 }}>{children}</div>
    </div>
  );
}

/* ----------  SIGNAL TAB  ---------- */
function EvidenceUnavailable({ loading, error }) {
  return (
    <div
      style={{
        background: loading ? C.warnBg : `${C.red}0D`,
        border: `1px solid ${loading ? C.warnBorder : `${C.red}33`}`,
        color: loading ? C.warnText : C.red,
        padding: "10px 14px",
        borderRadius: 6,
        marginBottom: 12,
        fontSize: 9,
        fontFamily: FONT_SANS,
        letterSpacing: "0.04em",
        lineHeight: 1.6,
        display: "flex", alignItems: "flex-start", gap: 8,
      }}
    >
      <span style={{ fontSize: 12, lineHeight: 1, marginTop: 1 }}>{loading ? "..." : "!"}</span>
      <div>
        <div style={{ fontWeight: 600, marginBottom: 3, fontSize: 10 }}>
          {loading ? "Model Evidence Loading..." : "Model Evidence Unavailable"}
        </div>
        <div style={{ color: loading ? `${C.warnText}99` : `${C.red}AA`, fontSize: 8 }}>
          SIGNAL and MODELS are waiting for backend `/api/model-scores`; browser simulation is not used as the primary score.
        </div>
      </div>
      {error && <div style={{ marginTop: 6 }}>{error}</div>}
    </div>
  );
}

function SignalTab({
  last, scores, ens, sig, sigColor, feat, accent,
  modelEvidence, modelEvidenceError, modelEvidenceLoading,
  modelQualityWarning, signalThresholdLabel, signalThresholds,
}) {
  if (!last) return <Empty />;
  const rsiState = last.rsi > 70 ? "OVERBOUGHT" : last.rsi < 30 ? "OVERSOLD" : "NEUTRAL";
  const rsiColor = last.rsi > 70 ? C.red : last.rsi < 30 ? C.green : C.textDim;
  const macdState = last.macdHist > 0 ? "BULLISH" : "BEARISH";
  const bbPos = feat ? feat.bbPos : 0.5;
  const bbState = bbPos > 0.8 ? "UPPER" : bbPos < 0.2 ? "LOWER" : "MIDDLE";
  const emaState = last.ema12 > last.ema26 ? "GOLDEN" : "DEATH";

  return (
    <>
      {scores ? (
        <div
          style={{
            background: C.bgDeep,
            border: `2px solid ${sigColor}`,
            padding: 16, marginBottom: 14,
            textAlign: "center", position: "relative",
            boxShadow: `0 0 24px ${sigColor}33, inset 0 0 24px ${sigColor}11`,
          }}
        >
          <div style={{ fontSize: 9, color: C.textMuted, letterSpacing: 2, marginBottom: 4 }}>
            BACKEND MODEL EVIDENCE
          </div>
          <div style={{ fontSize: 36, fontWeight: 700, color: sigColor, letterSpacing: 4, lineHeight: 1 }}>
            {sig}
          </div>
          <div style={{ fontSize: 11, color: C.textDim, marginTop: 6, letterSpacing: 1 }}>
            SCORE <span style={{ color: sigColor, fontWeight: 700, fontSize: 14 }}>{ens}</span> / 100
          </div>
          <div style={{ fontSize: 9, color: C.textMuted, marginTop: 6, lineHeight: 1.5 }}>
            {modelEvidence.model_kind} · {modelEvidence.provider} · rows {modelEvidence.evidence?.row_count ?? "N/A"}
          </div>
          {modelQualityWarning && (
            <div
              style={{
                display: "inline-block",
                marginTop: 10,
                padding: "5px 8px",
                border: `1px solid ${C.amber}`,
                color: C.amber,
                background: `${C.amber}14`,
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: 1,
              }}
            >
              {modelQualityWarning}
            </div>
          )}
          <div style={{ marginTop: 10, height: 4, background: C.border, position: "relative" }}>
            <div
              style={{
                position: "absolute", left: 0, top: 0, height: "100%",
                width: `${ens}%`, background: sigColor,
                boxShadow: `0 0 8px ${sigColor}`,
              }}
            />
            {Number.isFinite(Number(signalThresholds?.sell)) && (
              <div style={{ position: "absolute", left: `${Number(signalThresholds.sell)}%`, top: -2, width: 1, height: 8, background: C.textMuted }} />
            )}
            {Number.isFinite(Number(signalThresholds?.buy)) && (
              <div style={{ position: "absolute", left: `${Number(signalThresholds.buy)}%`, top: -2, width: 1, height: 8, background: C.textMuted }} />
            )}
          </div>
          {signalThresholdLabel && (
            <div style={{ fontSize: 8, color: C.textMuted, marginTop: 6 }}>{signalThresholdLabel}</div>
          )}
        </div>
      ) : (
        <EvidenceUnavailable loading={modelEvidenceLoading} error={modelEvidenceError} />
      )}

      {/* INDICATORS */}
      <SectionLabel>INDICATORS</SectionLabel>
      <IndRow label="RSI(14)" value={last.rsi?.toFixed(2)} state={rsiState} color={rsiColor} bar={last.rsi} barMax={100} />
      <IndRow label="MACD" value={last.macdHist?.toFixed(4)} state={macdState} color={last.macdHist > 0 ? C.green : C.red} />
      <IndRow label="BB%" value={(bbPos * 100).toFixed(1) + "%"} state={bbState} color={C.lstm} bar={bbPos * 100} barMax={100} />
      <IndRow label="EMA12/26" value={(last.ema12 - last.ema26).toFixed(2)} state={emaState} color={emaState === "GOLDEN" ? C.green : C.red} />

      {/* MODEL BARS */}
      <SectionLabel style={{ marginTop: 14 }}>MODELS</SectionLabel>
      {scores ? (
        <>
          <ModelBar label="Backend Main" value={scores.main} color={accent} weight={700} />
          <ModelBar label="LogReg" value={scores.lr} color={C.lr} />
          {scores.xgb != null && <ModelBar label="XGBoost" value={scores.xgb} color={C.xgb} />}
          {scores.lstm != null && <ModelBar label="LSTM" value={scores.lstm} color={C.lstm} />}
          {scores.rnn != null && <ModelBar label="RNN" value={scores.rnn} color={C.rnn} />}
        </>
      ) : (
        <ModelBar label="Backend Main" value={null} color={accent} weight={700} />
      )}
    </>
  );
}

function SectionLabel({ children, style }) {
  return (
    <div
      style={{
        fontFamily: FONT_SANS,
        fontSize: 9.5, letterSpacing: "0.10em", color: C.textLabel,
        fontWeight: 600, textTransform: "uppercase",
        margin: "10px 0 6px", paddingBottom: 5,
        borderBottom: `1px solid ${C.borderSoft}`,
        display: "flex", alignItems: "center", gap: 7,
        ...style,
      }}
    >
      <span style={{
        display: "inline-block", width: 14, height: 1,
        background: `linear-gradient(to right, ${C.borderHi}, transparent)`,
        flexShrink: 0,
      }} />
      {children}
    </div>
  );
}

function IndRow({ label, value, state, color, bar, barMax }) {
  return (
    <div style={{ marginBottom: 8, padding: "5px 0", borderBottom: `1px solid ${C.borderSoft}` }}>
      <div className="flex justify-between" style={{ alignItems: "baseline" }}>
        <span style={{ fontSize: 10, color: C.textDim, fontFamily: FONT_SANS, letterSpacing: "0.04em" }}>{label}</span>
        <span style={{ fontSize: 12, color: C.text, fontWeight: 600, letterSpacing: "0.02em" }}>{value}</span>
      </div>
      <div className="flex justify-between mt-0.5">
        <span style={{ fontSize: 9, color, fontFamily: FONT_SANS, letterSpacing: "0.05em" }}>{state}</span>
      </div>
      {bar != null && (
        <div style={{ height: 2, background: C.border, marginTop: 3 }}>
          <div
            style={{
              height: "100%", width: `${(bar / barMax) * 100}%`,
              background: color, transition: "width .3s",
            }}
          />
        </div>
      )}
    </div>
  );
}

function ModelBar({ label, value, color, weight }) {
  const displayValue = value == null || Number.isNaN(value) ? "N/A" : value;
  const width = value == null || Number.isNaN(value) ? 0 : Math.max(0, Math.min(100, value));
  return (
    <div style={{ marginBottom: 6 }}>
      <div className="flex justify-between" style={{ marginBottom: 2 }}>
        <span style={{ fontSize: 10, color: C.textDim, letterSpacing: 1, fontWeight: weight || 400 }}>
          {label}
        </span>
        <span style={{ fontSize: 11, color, fontWeight: weight || 600 }}>{displayValue}</span>
      </div>
      <div style={{ height: weight ? 6 : 4, background: C.border, position: "relative" }}>
        <div
          style={{
            height: "100%", width: `${width}%`, background: color,
            boxShadow: weight ? `0 0 6px ${color}` : "none",
            transition: "width .3s",
          }}
        />
      </div>
    </div>
  );
}

/* ----------  MODELS TAB  ---------- */
function ModelsTab({
  scores, ens, sig, sigColor,
  modelEvidence, modelEvidenceError, modelEvidenceLoading,
  modelQualityWarning, signalThresholds,
}) {
  if (!scores) {
    return <EvidenceUnavailable loading={modelEvidenceLoading} error={modelEvidenceError} />;
  }
  const data = [
    { name: "Main", value: scores.main, color: sigColor, required: true },
    { name: "LogReg", value: scores.lr, color: C.lr, required: true },
    { name: "XGBoost", value: scores.xgb, color: C.xgb },
    { name: "LSTM", value: scores.lstm, color: C.lstm },
    { name: "RNN", value: scores.rnn, color: C.rnn },
  ].filter((item) => item.required || (item.value != null && !Number.isNaN(Number(item.value))));
  const chartData = data.map((item) => ({ ...item, value: item.value == null ? 0 : item.value }));

  return (
    <>
      <div
        style={{
          background: C.bgDeep, border: `1px solid ${sigColor}`,
          padding: 12, marginBottom: 14, textAlign: "center",
        }}
      >
        <div style={{ fontSize: 9, color: C.textMuted, letterSpacing: 2 }}>ENSEMBLE</div>
        <div style={{ fontSize: 28, fontWeight: 700, color: sigColor, letterSpacing: 3 }}>
          {ens}
        </div>
        <div style={{ fontSize: 10, color: sigColor, letterSpacing: 2, marginTop: 2 }}>{sig}</div>
        {modelQualityWarning && (
          <div
            style={{
              display: "inline-block",
              marginTop: 8,
              padding: "5px 8px",
              border: `1px solid ${C.amber}`,
              color: C.amber,
              background: `${C.amber}14`,
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: 1,
            }}
          >
            {modelQualityWarning}
          </div>
        )}
      </div>

      <SectionLabel>BACKEND MODEL COMPARISON</SectionLabel>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={chartData} margin={{ top: 10, right: 4, left: -28, bottom: 0 }}>
          <CartesianGrid stroke={C.grid} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: C.textDim, fontSize: 9, fontFamily: FONT }} stroke={C.border} />
          <YAxis domain={[0, 100]} tick={{ fill: C.textDim, fontSize: 9, fontFamily: FONT }} stroke={C.border} />
          <Tooltip
            contentStyle={{ background: C.bgDeep, border: `1px solid ${C.borderHi}`, fontFamily: FONT, fontSize: 11, color: C.text }}
          />
          {Number.isFinite(Number(signalThresholds?.buy)) && (
            <ReferenceLine y={Number(signalThresholds.buy)} stroke={C.green} strokeDasharray="3 3" />
          )}
          {Number.isFinite(Number(signalThresholds?.sell)) && (
            <ReferenceLine y={Number(signalThresholds.sell)} stroke={C.red} strokeDasharray="3 3" />
          )}
          <Bar dataKey="value" radius={[2, 2, 0, 0]}>
            {data.map((d, i) => (
              <rect key={i} fill={d.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <SectionLabel style={{ marginTop: 14 }}>EVIDENCE</SectionLabel>
      {[
        { l: "Provider", v: modelEvidence.provider, c: C.text },
        { l: "Model", v: modelEvidence.model_kind, c: sigColor },
        { l: "OOF coverage", v: `${((modelEvidence.evidence?.oof_coverage ?? 0) * 100).toFixed(1)}%`, c: C.lr },
        { l: "Accuracy", v: (modelEvidence.evidence?.model_accuracy ?? 0).toFixed(3), c: C.hold },
        { l: "AUC", v: (modelEvidence.evidence?.model_auc ?? 0.5).toFixed(3), c: C.xgb },
      ].map((w) => (
        <div key={w.l} style={{ marginBottom: 4 }}>
          <div className="flex justify-between">
            <span style={{ fontSize: 10, color: w.c }}>{w.l}</span>
            <span style={{ fontSize: 10, color: C.textDim }}>{w.v}</span>
          </div>
        </div>
      ))}

      <SectionLabel style={{ marginTop: 14 }}>MODEL SCORES</SectionLabel>
      {data.map((d) => (
        <div
          key={d.name}
          style={{
            padding: "6px 8px", marginBottom: 5,
            background: C.bgDeep, borderLeft: `2px solid ${d.color}`,
          }}
        >
          <div className="flex justify-between" style={{ marginBottom: 2 }}>
            <span style={{ color: d.color, fontSize: 10, fontWeight: 600, letterSpacing: 1 }}>
              {d.name}
            </span>
            <span style={{ color: d.color, fontSize: 11, fontWeight: 600 }}>{d.value}</span>
          </div>
        </div>
      ))}
    </>
  );
}

/* ----------  BACKTEST TAB  ---------- */
function BacktestTab({ backtest, market, fmtMoney, accent }) {
  if (!backtest) return <Empty />;
  const trades = backtest.trades.slice(-12).reverse();
  return (
    <>
      <SectionLabel>EQUITY CURVE · ML vs B&H</SectionLabel>
      <ResponsiveContainer width="100%" height={170}>
        <LineChart data={backtest.eq} margin={{ top: 6, right: 4, left: -10, bottom: 0 }}>
          <CartesianGrid stroke={C.grid} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="date" tick={{ fill: C.textDim, fontSize: 8, fontFamily: FONT }} stroke={C.border} interval="preserveStartEnd" minTickGap={30} />
          <YAxis tick={{ fill: C.textDim, fontSize: 8, fontFamily: FONT }} stroke={C.border} domain={["auto", "auto"]} tickFormatter={(v) => "$" + (v / 1000).toFixed(1) + "k"} />
          <Tooltip
            contentStyle={{ background: C.bgDeep, border: `1px solid ${accent}`, fontFamily: FONT, fontSize: 10, color: C.text }}
            labelStyle={{ color: accent }}
            formatter={(v) => "$" + Number(v).toLocaleString()}
          />
          <ReferenceLine y={backtest.initial} stroke={C.textMuted} strokeDasharray="2 4" />
          <Line type="monotone" dataKey="bh" stroke={C.textDim} strokeWidth={1.2} dot={false} name="Buy&Hold" />
          <Line type="monotone" dataKey="ml" stroke={accent} strokeWidth={2} dot={false} name="ML" />
        </LineChart>
      </ResponsiveContainer>

      <SectionLabel style={{ marginTop: 12 }}>STATS</SectionLabel>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
        <Stat label="ML RETURN" value={`${(backtest.mlRet * 100).toFixed(2)}%`} color={backtest.mlRet >= 0 ? C.green : C.red} />
        <Stat label="B&H RETURN" value={`${(backtest.bhRet * 100).toFixed(2)}%`} color={backtest.bhRet >= 0 ? C.green : C.red} />
        <Stat label="ALPHA" value={`${(backtest.alpha * 100).toFixed(2)}%`} color={backtest.alpha >= 0 ? C.green : C.red} highlight />
        <Stat label="SHARPE" value={backtest.sharpe.toFixed(2)} color={backtest.sharpe >= 1 ? C.green : backtest.sharpe >= 0 ? C.amber : C.red} />
        <Stat label="WIN RATE" value={`${(backtest.winRate * 100).toFixed(1)}%`} color={backtest.winRate >= 0.5 ? C.green : C.amber} />
        <Stat label="TRADES" value={`${backtest.totalTrades} (${backtest.completedTrades})`} color={C.text} />
        <Stat label="ML FINAL" value={fmtMoney(backtest.finalVal)} color={C.text} />
        <Stat label="B&H FINAL" value={fmtMoney(backtest.bhFinal)} color={C.textDim} />
      </div>

      <SectionLabel style={{ marginTop: 12 }}>RECENT TRADES (last 12)</SectionLabel>
      <div style={{ maxHeight: 200, overflowY: "auto" }}>
        {trades.length === 0 ? (
          <div style={{ color: C.textDim, fontSize: 10, textAlign: "center", padding: 12 }}>
            no trades signaled
          </div>
        ) : (
          trades.map((t, i) => (
            <div
              key={i}
              style={{
                display: "grid",
                gridTemplateColumns: "60px 50px 1fr 38px",
                alignItems: "center",
                padding: "4px 6px", marginBottom: 3,
                background: C.bgDeep, fontSize: 10,
                borderLeft: `2px solid ${t.action === "BUY" ? C.green : C.red}`,
              }}
            >
              <span style={{ color: C.textDim, fontSize: 9 }}>{t.date.slice(5)}</span>
              <span style={{ color: t.action === "BUY" ? C.green : C.red, fontWeight: 600, letterSpacing: 1 }}>
                {t.action}
              </span>
              <span style={{ color: C.text, textAlign: "right", paddingRight: 8 }}>
                {market === "US" ? `$${t.price.toFixed(2)}` : `₩${Math.round(t.price).toLocaleString()}`}
              </span>
              <span style={{ color: C.textDim, fontSize: 9, textAlign: "right" }}>{t.score}</span>
            </div>
          ))
        )}
      </div>
    </>
  );
}

/* ----------  PAPER TAB  ---------- */
function PaperTradingTab({ status, loading, error, accent, fmtMoney }) {
  if (loading && !status) return <Empty />;
  if (error) {
    return (
      <div style={{ padding: 12, color: C.red, background: C.bgDeep, border: `1px solid ${C.red}`, fontSize: 10 }}>
        {error}
      </div>
    );
  }
  const latestRun = status?.latest_run;
  const positions = Array.isArray(status?.positions) ? status.positions : [];
  const rejected = Array.isArray(status?.rejected_signals) ? status.rejected_signals : [];
  const equityCurve = Array.isArray(status?.equity_curve) ? status.equity_curve : [];
  const lastEquity = equityCurve[equityCurve.length - 1]?.equity;
  const drawdown = status?.drawdown || {};
  const gate = status?.model_quality_gate || {};
  const krxPilot = status?.krx_pilot || null;
  const krxPositions = Array.isArray(krxPilot?.positions) ? krxPilot.positions : [];
  const krxRejected = Array.isArray(krxPilot?.rejected_signals) ? krxPilot.rejected_signals : [];
  const krxEquityCurve = Array.isArray(krxPilot?.equity_curve) ? krxPilot.equity_curve : [];
  const krxLastEquity = krxEquityCurve[krxEquityCurve.length - 1]?.equity;
  const krxDrawdown = krxPilot?.drawdown || {};
  const krxBenchmark = krxPilot?.benchmark || {};
  const krxMoney = (value) => `₩${Math.round(Number(value || 0)).toLocaleString()}`;

  return (
    <>
      <div
        style={{
          background: C.bgDeep,
          border: `1px solid ${accent}`,
          padding: 10,
          marginBottom: 12,
        }}
      >
        <div style={{ color: accent, fontSize: 10, fontWeight: 700, letterSpacing: 1.2 }}>
          Paper trading only - no broker orders
        </div>
        <div style={{ color: C.textDim, fontSize: 9, lineHeight: 1.6, marginTop: 4 }}>
          Status {status?.status || "EMPTY"} · Run {latestRun?.run_id || "no run yet"}
        </div>
      </div>

      <SectionLabel>SUMMARY</SectionLabel>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
        <Stat label="POSITIONS" value={positions.length} color={positions.length ? C.green : C.textDim} />
        <Stat label="REJECTED" value={rejected.length} color={rejected.length ? C.amber : C.textDim} />
        <Stat label="EQUITY" value={Number.isFinite(Number(lastEquity)) ? fmtMoney(Number(lastEquity)) : "N/A"} color={C.text} />
        <Stat
          label="MAX DD"
          value={Number.isFinite(Number(drawdown.max_drawdown_pct)) ? `${Number(drawdown.max_drawdown_pct).toFixed(2)}%` : "N/A"}
          color={drawdown.promotion_hard_fail ? C.red : C.textDim}
        />
      </div>

      <SectionLabel style={{ marginTop: 14 }}>VIRTUAL POSITIONS</SectionLabel>
      {positions.length === 0 ? (
        <div style={{ color: C.textDim, fontSize: 10, padding: "8px 0" }}>no virtual positions</div>
      ) : (
        positions.map((p) => (
          <div
            key={`${p.run_id}-${p.ticker}`}
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 58px 74px",
              gap: 6,
              padding: "7px 8px",
              marginBottom: 5,
              background: C.bgDeep,
              borderLeft: `2px solid ${C.green}`,
              fontSize: 10,
            }}
          >
            <span style={{ color: C.text, fontWeight: 700 }}>{p.ticker}</span>
            <span style={{ color: C.textDim, textAlign: "right" }}>{p.shares} sh</span>
            <span style={{ color: C.text, textAlign: "right" }}>{fmtMoney(Number(p.market_value || 0))}</span>
          </div>
        ))
      )}

      <SectionLabel style={{ marginTop: 14 }}>REJECTED SIGNALS</SectionLabel>
      {rejected.length === 0 ? (
        <div style={{ color: C.textDim, fontSize: 10, padding: "8px 0" }}>no rejected signals</div>
      ) : (
        rejected.slice(0, 8).map((r, i) => (
          <div
            key={`${r.ticker}-${r.reason}-${i}`}
            style={{
              display: "grid",
              gridTemplateColumns: "84px 1fr",
              gap: 8,
              padding: "7px 8px",
              marginBottom: 5,
              background: C.bgDeep,
              borderLeft: `2px solid ${C.amber}`,
              fontSize: 10,
            }}
          >
            <span style={{ color: C.text, fontWeight: 700 }}>{r.ticker}</span>
            <span style={{ color: C.amber }}>{r.reason}</span>
          </div>
        ))
      )}

      <SectionLabel style={{ marginTop: 14 }}>MODEL QUALITY GATE</SectionLabel>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 6 }}>
        <Stat label="MIN AUC" value={Number(gate.min_model_auc ?? 0.55).toFixed(2)} color={C.xgb} />
        <Stat label="MIN ACC" value={Number(gate.min_model_accuracy ?? 0.52).toFixed(2)} color={C.hold} />
        <Stat label="MIN OOF" value={`${(Number(gate.min_oof_coverage ?? 0.8) * 100).toFixed(0)}%`} color={C.lr} />
      </div>

      {krxPilot && (
        <>
          <SectionLabel style={{ marginTop: 14 }}>KRX PILOT</SectionLabel>
          <div style={{ background: C.bgDeep, border: `1px solid ${C.krx}`, padding: 10, marginBottom: 10 }}>
            <div style={{ color: C.krx, fontSize: 10, fontWeight: 700, letterSpacing: 1.2 }}>
              {krxPilot.pilot_label || "KRX paper trading pilot"}
            </div>
            <div style={{ color: C.textDim, fontSize: 9, lineHeight: 1.6, marginTop: 4 }}>
              Paper trading only - no broker orders · Status {krxPilot.status || "EMPTY"} · Run {krxPilot.latest_run?.run_id || "no run yet"}
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 10 }}>
            <Stat label="KRX EQUITY" value={Number.isFinite(Number(krxLastEquity)) ? krxMoney(krxLastEquity) : "N/A"} color={C.text} />
            <Stat
              label="KRX MAX DD"
              value={Number.isFinite(Number(krxDrawdown.max_drawdown_pct)) ? `${Number(krxDrawdown.max_drawdown_pct).toFixed(2)}%` : "N/A"}
              color={krxDrawdown.not_promotable ? C.red : C.textDim}
            />
            <Stat label="BENCHMARK" value={krxBenchmark.ticker || "N/A"} color={C.krx} />
            <Stat label="BENCH STATUS" value={krxBenchmark.status || "N/A"} color={krxBenchmark.not_promotable ? C.red : C.green} />
          </div>
          {krxPositions.length === 0 ? (
            <div style={{ color: C.textDim, fontSize: 10, padding: "8px 0" }}>no KRX virtual positions</div>
          ) : (
            krxPositions.map((p) => (
              <div
                key={`${p.run_id || "krx"}-${p.ticker}`}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 58px 82px",
                  gap: 6,
                  padding: "7px 8px",
                  marginBottom: 5,
                  background: C.bgDeep,
                  borderLeft: `2px solid ${C.krx}`,
                  fontSize: 10,
                }}
              >
                <span style={{ color: C.text, fontWeight: 700 }}>{p.ticker}</span>
                <span style={{ color: C.textDim, textAlign: "right" }}>{p.shares} sh</span>
                <span style={{ color: C.text, textAlign: "right" }}>{krxMoney(p.market_value)}</span>
              </div>
            ))
          )}
          {krxRejected.length > 0 && (
            krxRejected.slice(0, 8).map((r, i) => (
              <div
                key={`${r.ticker}-${r.reason}-${i}`}
                style={{
                  display: "grid",
                  gridTemplateColumns: "84px 1fr",
                  gap: 8,
                  padding: "7px 8px",
                  marginBottom: 5,
                  background: C.bgDeep,
                  borderLeft: `2px solid ${C.amber}`,
                  fontSize: 10,
                }}
              >
                <span style={{ color: C.text, fontWeight: 700 }}>{r.ticker}</span>
                <span style={{ color: C.amber }}>{r.reason}</span>
              </div>
            ))
          )}
        </>
      )}
    </>
  );
}

function Stat({ label, value, color, highlight }) {
  return (
    <div
      style={{
        background: highlight ? C.panelHi : C.bgDeep,
        border: `1px solid ${highlight ? C.borderHi : C.border}`,
        padding: "6px 8px",
      }}
    >
      <div style={{ fontSize: 8, color: C.textMuted, letterSpacing: 1.5 }}>{label}</div>
      <div style={{ fontSize: 13, color, fontWeight: 600, marginTop: 2 }}>{value}</div>
    </div>
  );
}

function Empty() {
  return (
    <div style={{ color: C.textDim, fontSize: 11, textAlign: "center", padding: 32, letterSpacing: 1 }}>
      ◌ DATA LOADING
    </div>
  );
}

/* ----------  BENCHMARK PANEL  ---------- */
function BenchmarkPanel({ bench, accent, market, onClose, onPick }) {
  return (
    <div>
      <div
        style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          marginBottom: 14, paddingBottom: 10, borderBottom: `1px solid ${C.border}`,
        }}
      >
        <div>
          <div style={{ fontSize: 18, fontWeight: 700, color: accent, letterSpacing: 3 }}>
            ◊ BENCHMARK · {market}
          </div>
          <div style={{ fontSize: 10, color: C.textDim, marginTop: 2 }}>
            ENSEMBLE SCAN · ALL SYMBOLS · CLIENT-SIDE INFERENCE
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            padding: "6px 14px", background: "transparent",
            border: `1px solid ${C.border}`, color: C.textDim,
            fontFamily: FONT, fontSize: 10, letterSpacing: 1.5, cursor: "pointer",
          }}
        >
          ✕ CLOSE
        </button>
      </div>

      {bench.loading && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 10, color: C.textDim, marginBottom: 4 }}>
            SCANNING... {Math.round(bench.progress * 100)}%
          </div>
          <div style={{ height: 4, background: C.border }}>
            <div
              style={{
                height: "100%", width: `${bench.progress * 100}%`,
                background: accent, boxShadow: `0 0 8px ${accent}`,
                transition: "width .3s",
              }}
            />
          </div>
        </div>
      )}

      <div style={{ background: C.panel, border: `1px solid ${C.border}` }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "60px 1fr 90px 60px 50px 50px 50px 50px 70px 60px",
            background: C.bgDeep, padding: "8px 10px",
            borderBottom: `1px solid ${C.border}`,
            fontSize: 9, letterSpacing: 1.5, color: C.textMuted, fontWeight: 600,
          }}
        >
          <span>RANK</span>
          <span>SYMBOL</span>
          <span style={{ textAlign: "right" }}>PRICE</span>
          <span style={{ textAlign: "right" }}>CHG</span>
          <span style={{ textAlign: "center" }}>LSTM</span>
          <span style={{ textAlign: "center" }}>LR</span>
          <span style={{ textAlign: "center" }}>XGB</span>
          <span style={{ textAlign: "center" }}>RNN</span>
          <span style={{ textAlign: "center", color: accent }}>ENS</span>
          <span style={{ textAlign: "center" }}>SIG</span>
        </div>

        {bench.rows.map((r, i) => {
          const sigColor = r.sig === "BUY" ? C.buy : r.sig === "SELL" ? C.sell : C.hold;
          return (
            <div
              key={r.symbol}
              onClick={() => onPick(r.symbol)}
              style={{
                display: "grid",
                gridTemplateColumns: "60px 1fr 90px 60px 50px 50px 50px 50px 70px 60px",
                padding: "10px",
                borderBottom: `1px solid ${C.border}`,
                cursor: "pointer", fontSize: 11,
                background: i === 0 ? C.panelHi : "transparent",
                transition: "background .15s",
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = C.panel2; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = i === 0 ? C.panelHi : "transparent"; }}
            >
              <span style={{ color: i < 3 ? accent : C.textDim, fontWeight: 600 }}>
                {i === 0 ? "★ 1" : `#${i + 1}`}
              </span>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span style={{ color: C.text, fontWeight: 600, letterSpacing: 1 }}>
                  {r.symbol.replace(".KS", "")}
                </span>
                <span style={{ fontSize: 9, color: C.textDim }}>
                  {r.name}
                </span>
              </div>
              <span style={{ textAlign: "right", color: C.text, fontWeight: 500 }}>
                {market === "US" ? `$${r.price.toFixed(2)}` : `₩${Math.round(r.price).toLocaleString()}`}
              </span>
              <span style={{ textAlign: "right", color: r.chg >= 0 ? C.green : C.red, fontSize: 10 }}>
                {r.chg >= 0 ? "+" : ""}{r.chg.toFixed(2)}%
              </span>
              <ScoreCell value={r.lstm} color={C.lstm} />
              <ScoreCell value={r.lr} color={C.lr} />
              <ScoreCell value={r.xgb} color={C.xgb} />
              <ScoreCell value={r.rnn} color={C.rnn} />
              <span
                style={{
                  textAlign: "center", color: accent,
                  fontWeight: 700, fontSize: 14,
                }}
              >
                {r.ens}
              </span>
              <span
                style={{
                  textAlign: "center",
                  color: sigColor, fontWeight: 700, letterSpacing: 1, fontSize: 10,
                  background: sigColor + "22", padding: "2px 0", borderRadius: 2,
                }}
              >
                {r.sig}
              </span>
            </div>
          );
        })}

        {bench.rows.length === 0 && !bench.loading && (
          <div style={{ padding: 32, textAlign: "center", color: C.textDim }}>
            no rows
          </div>
        )}
      </div>

      {!bench.loading && bench.rows.length > 0 && (
        <div
          style={{
            marginTop: 14, padding: 10, background: C.panel,
            border: `1px solid ${C.border}`, fontSize: 10, color: C.textDim,
            letterSpacing: 1, lineHeight: 1.6,
          }}
        >
          <div style={{ color: accent, fontWeight: 600, marginBottom: 4 }}>
            ▸ BRIEF · 판정 / 근거 / 행동
          </div>
          <div>
            ◇ TOP PICK :{" "}
            <span style={{ color: C.text }}>{bench.rows[0].name}</span>{" "}
            (ENS{" "}
            <span style={{ color: accent, fontWeight: 600 }}>{bench.rows[0].ens}</span>) ·{" "}
            SIG <span style={{ color: bench.rows[0].sig === "BUY" ? C.buy : bench.rows[0].sig === "SELL" ? C.sell : C.hold, fontWeight: 600 }}>
              {bench.rows[0].sig}
            </span>
          </div>
          <div>
            ◇ BUY signals: <span style={{ color: C.buy }}>{bench.rows.filter((r) => r.sig === "BUY").length}</span> ·{" "}
            HOLD: <span style={{ color: C.hold }}>{bench.rows.filter((r) => r.sig === "HOLD").length}</span> ·{" "}
            SELL: <span style={{ color: C.sell }}>{bench.rows.filter((r) => r.sig === "SELL").length}</span>
          </div>
          <div>
            ◇ Click any row to load full chart · Data source labels come from API results
          </div>
        </div>
      )}
    </div>
  );
}

function ScoreCell({ value, color }) {
  return (
    <div style={{ textAlign: "center", position: "relative" }}>
      <div style={{ fontSize: 11, color, fontWeight: 600 }}>{value}</div>
      <div
        style={{
          height: 2, background: C.border, marginTop: 2, marginInline: 6,
        }}
      >
        <div
          style={{
            height: "100%", width: `${value}%`, background: color,
            transition: "width .3s",
          }}
        />
      </div>
    </div>
  );
}
