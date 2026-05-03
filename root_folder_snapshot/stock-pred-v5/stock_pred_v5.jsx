import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
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

/* ============================================================
 * STOCK·PRED v5.0  —  Dual-Market ML Dashboard
 * Markets: US (NYSE/NASDAQ) + KRX (Korea Exchange)
 * Models : Logistic Regression · XGBoost-sim · LSTM-sim · Elman RNN
 * Engine : Yahoo Finance via allorigins proxy + synthetic fallback
 * ============================================================ */

const C = {
  bg: "#050A0E",
  bgDeep: "#02060A",
  panel: "#0A1218",
  panel2: "#0E1822",
  panelHi: "#13202C",
  border: "#1A2A38",
  borderHi: "#243648",
  text: "#D4E1EC",
  textDim: "#6B7E8E",
  textMuted: "#3F5060",
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
};

const FONT =
  '"JetBrains Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, monospace';

const US_SYMBOLS = [
  { symbol: "AAPL", name: "Apple Inc." },
  { symbol: "MSFT", name: "Microsoft" },
  { symbol: "NVDA", name: "NVIDIA" },
  { symbol: "TSLA", name: "Tesla" },
  { symbol: "AMZN", name: "Amazon" },
  { symbol: "GOOGL", name: "Alphabet" },
  { symbol: "META", name: "Meta" },
  { symbol: "SPY", name: "S&P 500 ETF" },
  { symbol: "QQQ", name: "Nasdaq 100 ETF" },
];

const KRX_SYMBOLS = [
  { symbol: "005930.KS", name: "삼성전자", basePrice: 75000 },
  { symbol: "000660.KS", name: "SK하이닉스", basePrice: 180000 },
  { symbol: "005380.KS", name: "현대차", basePrice: 220000 },
  { symbol: "005490.KS", name: "POSCO홀딩스", basePrice: 380000 },
  { symbol: "035420.KS", name: "NAVER", basePrice: 195000 },
  { symbol: "035720.KS", name: "카카오", basePrice: 42000 },
  { symbol: "051910.KS", name: "LG화학", basePrice: 320000 },
  { symbol: "006400.KS", name: "삼성SDI", basePrice: 280000 },
  { symbol: "003670.KS", name: "포스코퓨처엠", basePrice: 195000 },
];

const US_BASE = {
  AAPL: 190, MSFT: 410, NVDA: 880, TSLA: 240, AMZN: 175,
  GOOGL: 165, META: 480, SPY: 510, QQQ: 430,
};

/* ----------  PRNG / hash  ---------- */
function mulberry32(seed) {
  return function () {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = seed;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hashSeed(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/* ----------  Synthetic OHLCV  ---------- */
function generateSynthetic(symbol, days = 130) {
  const rng = mulberry32(hashSeed(symbol));
  const krx = KRX_SYMBOLS.find((s) => s.symbol === symbol);
  const base = krx ? krx.basePrice : US_BASE[symbol] || 100;
  const vol = 0.018 + rng() * 0.018;
  const trend = (rng() - 0.45) * 0.001;

  let price = base * (0.85 + rng() * 0.25);
  const out = [];
  const now = Date.now();
  for (let i = days - 1; i >= 0; i--) {
    const t = now - i * 86_400_000;
    const dt = new Date(t);
    if (dt.getDay() === 0 || dt.getDay() === 6) continue;
    const drift = trend + (rng() - 0.5) * vol;
    const open = price;
    const close = price * (1 + drift);
    const intra = vol * 0.55;
    const high = Math.max(open, close) * (1 + rng() * intra);
    const low = Math.min(open, close) * (1 - rng() * intra);
    const volBase = krx ? 5_000_000 : 30_000_000;
    const volume = Math.floor(volBase * (0.45 + rng() * 1.1));
    out.push({
      date: dt.toISOString().slice(0, 10),
      timestamp: t,
      open, high, low, close, volume,
    });
    price = close;
  }
  return out;
}

/* ----------  Yahoo Finance via allorigins  ---------- */
async function fetchSymbol(symbol) {
  try {
    const yahoo = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=6mo`;
    const url = `https://api.allorigins.win/raw?url=${encodeURIComponent(yahoo)}`;
    const ctrl = new AbortController();
    const tid = setTimeout(() => ctrl.abort(), 9000);
    const res = await fetch(url, { signal: ctrl.signal });
    clearTimeout(tid);
    if (!res.ok) throw new Error("net");
    const j = await res.json();
    const r = j?.chart?.result?.[0];
    if (!r) throw new Error("empty");
    const ts = r.timestamp || [];
    const q = r.indicators?.quote?.[0] || {};
    const data = [];
    for (let i = 0; i < ts.length; i++) {
      if (q.close[i] == null) continue;
      data.push({
        date: new Date(ts[i] * 1000).toISOString().slice(0, 10),
        timestamp: ts[i] * 1000,
        open: q.open[i] ?? q.close[i],
        high: q.high[i] ?? q.close[i],
        low: q.low[i] ?? q.close[i],
        close: q.close[i],
        volume: q.volume[i] ?? 0,
      });
    }
    if (data.length < 30) throw new Error("short");
    return { data, source: "YAHOO" };
  } catch (e) {
    return { data: generateSynthetic(symbol, 130), source: "SYN" };
  }
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
function signalFromScore(s) {
  if (s >= 65) return "BUY";
  if (s <= 35) return "SELL";
  return "HOLD";
}

/* ----------  Backtest  ---------- */
function runBacktest(en) {
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
    const sig = signalFromScore(ens);
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
  const [selected, setSelected] = useState("AAPL");
  const [cache, setCache] = useState({});
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState("SIGNAL");
  const [bench, setBench] = useState({ open: false, rows: [], loading: false, progress: 0 });
  const [clock, setClock] = useState("");
  const [exportFlash, setExportFlash] = useState("");

  const symbols = market === "US" ? US_SYMBOLS : KRX_SYMBOLS;
  const accent = market === "US" ? C.us : C.krx;
  const currency = market === "US" ? "$" : "₩";

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

  /* fetch on selection */
  useEffect(() => {
    if (cache[selected]) return;
    let cancelled = false;
    setLoading(true);
    fetchSymbol(selected).then((res) => {
      if (cancelled) return;
      setCache((c) => ({ ...c, [selected]: { ...res, fetchedAt: Date.now() } }));
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [selected, cache]);

  /* market toggle: reset to first symbol */
  useEffect(() => {
    setSelected(market === "US" ? US_SYMBOLS[0].symbol : KRX_SYMBOLS[0].symbol);
    setBench({ open: false, rows: [], loading: false, progress: 0 });
  }, [market]);

  const cur = cache[selected];
  const enriched = useMemo(() => (cur ? enrich(cur.data) : []), [cur]);
  const lastIdx = enriched.length - 1;
  const last = lastIdx >= 0 ? enriched[lastIdx] : null;
  const prev = lastIdx > 0 ? enriched[lastIdx - 1] : null;
  const change = last && prev ? last.close - prev.close : 0;
  const changePct = last && prev ? (change / prev.close) * 100 : 0;

  const feat = useMemo(() => (last ? features(enriched, lastIdx) : null), [enriched, lastIdx, last]);
  const scores = useMemo(() => {
    if (!last) return null;
    return {
      lr: lrPredict(feat),
      xgb: xgbPredict(feat),
      lstm: lstmPredict(enriched, lastIdx),
      rnn: rnnPredict(enriched, lastIdx),
    };
  }, [feat, enriched, lastIdx, last]);
  const ens = scores ? ensembleScore(scores) : null;
  const sig = ens != null ? signalFromScore(ens) : null;

  const backtest = useMemo(() => (enriched.length > 35 ? runBacktest(enriched) : null), [enriched]);

  /* prefetch other symbols' last-prices for sidebar */
  const [sidebarSnap, setSidebarSnap] = useState({});
  useEffect(() => {
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
        const res = await fetchSymbol(s.symbol);
        if (cancel) return;
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
  }, [market]);

  /* benchmark scan */
  const runBenchmark = useCallback(async () => {
    setBench({ open: true, rows: [], loading: true, progress: 0 });
    const rows = [];
    let done = 0;
    for (const s of symbols) {
      let pkg = cache[s.symbol];
      if (!pkg) {
        pkg = await fetchSymbol(s.symbol);
        setCache((c) => ({ ...c, [s.symbol]: { ...pkg, fetchedAt: Date.now() } }));
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
          rsi: en[i].rsi, ...sc, ens: e, sig: signalFromScore(e),
          src: pkg.source,
        });
      }
      done++;
      setBench((b) => ({ ...b, progress: done / symbols.length }));
    }
    rows.sort((a, b) => b.ens - a.ens);
    setBench({ open: true, rows, loading: false, progress: 1 });
  }, [cache, symbols]);

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
      models: scores,
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
    if (!cur || !last || !scores) return;
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
| Model | Score |
|---|---|
| LSTM (sim) | ${scores.lstm} |
| Logistic Regression | ${scores.lr} |
| XGBoost (sim) | ${scores.xgb} |
| Elman RNN | ${scores.rnn} |
| **Ensemble** | **${ens}** |

## Signal: **${sig}**

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

  /* ======================== RENDER ======================== */
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
              ML ENSEMBLE · DUAL MARKET · CLIENT-SIDE INFERENCE
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
                color: C.textMuted, fontSize: 9, letterSpacing: 2,
                padding: "4px 6px 8px",
              }}
            >
              ── SYMBOLS · {market} ──
            </div>
            {symbols.map((s) => {
              const snap = sidebarSnap[s.symbol];
              const isActive = s.symbol === selected;
              return (
                <button
                  key={s.symbol}
                  onClick={() => setSelected(s.symbol)}
                  style={{
                    width: "100%", textAlign: "left",
                    padding: "8px 10px", marginBottom: 3,
                    background: isActive ? C.panelHi : "transparent",
                    borderLeft: `2px solid ${isActive ? accent : "transparent"}`,
                    cursor: "pointer", border: "none",
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
                    {snap && (
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
                    {snap && (
                      <span style={{ fontSize: 9, color: C.textDim }}>
                        {market === "US"
                          ? `$${snap.price.toFixed(2)}`
                          : `₩${Math.round(snap.price).toLocaleString()}`}
                      </span>
                    )}
                  </div>
                  {snap?.src === "SYN" && (
                    <div style={{ fontSize: 8, color: C.amber, letterSpacing: 1 }}>SYN</div>
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
              <div>BUY ≥ 65 · HOLD 36-64 · SELL ≤ 35</div>
              <div style={{ marginTop: 4 }}>
                ENS = LSTM·30 + LR·25 + XGB·25 + RNN·20
              </div>
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
                  setSelected(sym);
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
              {["SIGNAL", "MODELS", "BACKTEST"].map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  style={{
                    flex: 1, padding: "9px 0",
                    background: tab === t ? C.panelHi : "transparent",
                    border: "none",
                    borderBottom: `2px solid ${tab === t ? accent : "transparent"}`,
                    color: tab === t ? accent : C.textDim,
                    fontFamily: FONT, fontWeight: 600, letterSpacing: 1.5, fontSize: 10,
                    cursor: "pointer", transition: "all .15s",
                  }}
                >
                  {t}
                </button>
              ))}
            </div>

            <div style={{ padding: 12 }}>
              {tab === "SIGNAL" && (
                <SignalTab
                  last={last}
                  scores={scores}
                  ens={ens}
                  sig={sig}
                  sigColor={sigColor}
                  feat={feat}
                  accent={accent}
                />
              )}
              {tab === "MODELS" && (
                <ModelsTab scores={scores} ens={ens} sig={sig} sigColor={sigColor} />
              )}
              {tab === "BACKTEST" && (
                <BacktestTab
                  backtest={backtest}
                  market={market}
                  fmtMoney={fmtMoney}
                  accent={accent}
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
}) {
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
          display: "flex", alignItems: "baseline", gap: 14, marginBottom: 12,
          paddingBottom: 10, borderBottom: `1px solid ${C.border}`,
          flexWrap: "wrap",
        }}
      >
        <div style={{ fontSize: 22, fontWeight: 700, color: accent, letterSpacing: 2 }}>
          {selected.replace(".KS", "")}
        </div>
        <div style={{ color: C.textDim, fontSize: 11 }}>{symbolName}</div>
        <div style={{ fontSize: 22, fontWeight: 600 }}>{fmtMoney(last.close)}</div>
        <div
          style={{
            color: change >= 0 ? C.green : C.red,
            fontSize: 13, fontWeight: 600,
          }}
        >
          {change >= 0 ? "▲" : "▼"} {Math.abs(change).toFixed(market === "US" ? 2 : 0)}{" "}
          ({changePct >= 0 ? "+" : ""}{changePct.toFixed(2)}%)
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <Badge label="SRC" value={cur.source} color={cur.source === "YAHOO" ? C.green : C.amber} />
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
function SignalTab({ last, scores, ens, sig, sigColor, feat, accent }) {
  if (!last || !scores) return <Empty />;
  const rsiState = last.rsi > 70 ? "OVERBOUGHT" : last.rsi < 30 ? "OVERSOLD" : "NEUTRAL";
  const rsiColor = last.rsi > 70 ? C.red : last.rsi < 30 ? C.green : C.textDim;
  const macdState = last.macdHist > 0 ? "BULLISH" : "BEARISH";
  const bbPos = feat ? feat.bbPos : 0.5;
  const bbState = bbPos > 0.8 ? "UPPER" : bbPos < 0.2 ? "LOWER" : "MIDDLE";
  const emaState = last.ema12 > last.ema26 ? "GOLDEN" : "DEATH";

  return (
    <>
      {/* SIGNAL CARD */}
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
          ENSEMBLE SIGNAL
        </div>
        <div style={{ fontSize: 36, fontWeight: 700, color: sigColor, letterSpacing: 4, lineHeight: 1 }}>
          {sig}
        </div>
        <div style={{ fontSize: 11, color: C.textDim, marginTop: 6, letterSpacing: 1 }}>
          SCORE <span style={{ color: sigColor, fontWeight: 700, fontSize: 14 }}>{ens}</span> / 100
        </div>
        {/* score bar */}
        <div style={{ marginTop: 10, height: 4, background: C.border, position: "relative" }}>
          <div
            style={{
              position: "absolute", left: 0, top: 0, height: "100%",
              width: `${ens}%`, background: sigColor,
              boxShadow: `0 0 8px ${sigColor}`,
            }}
          />
          <div style={{ position: "absolute", left: "35%", top: -2, width: 1, height: 8, background: C.textMuted }} />
          <div style={{ position: "absolute", left: "65%", top: -2, width: 1, height: 8, background: C.textMuted }} />
        </div>
      </div>

      {/* INDICATORS */}
      <SectionLabel>INDICATORS</SectionLabel>
      <IndRow label="RSI(14)" value={last.rsi?.toFixed(2)} state={rsiState} color={rsiColor} bar={last.rsi} barMax={100} />
      <IndRow label="MACD" value={last.macdHist?.toFixed(4)} state={macdState} color={last.macdHist > 0 ? C.green : C.red} />
      <IndRow label="BB%" value={(bbPos * 100).toFixed(1) + "%"} state={bbState} color={C.lstm} bar={bbPos * 100} barMax={100} />
      <IndRow label="EMA12/26" value={(last.ema12 - last.ema26).toFixed(2)} state={emaState} color={emaState === "GOLDEN" ? C.green : C.red} />

      {/* MODEL BARS */}
      <SectionLabel style={{ marginTop: 14 }}>MODELS</SectionLabel>
      <ModelBar label="LSTM" value={scores.lstm} color={C.lstm} />
      <ModelBar label="LogReg" value={scores.lr} color={C.lr} />
      <ModelBar label="XGBoost" value={scores.xgb} color={C.xgb} />
      <ModelBar label="RNN" value={scores.rnn} color={C.rnn} />
      <ModelBar label="ENSEMBLE" value={ens} color={accent} weight={700} />
    </>
  );
}

function SectionLabel({ children, style }) {
  return (
    <div
      style={{
        fontSize: 9, letterSpacing: 2, color: C.textMuted, fontWeight: 600,
        margin: "8px 0 6px", paddingBottom: 4,
        borderBottom: `1px dashed ${C.border}`, ...style,
      }}
    >
      ── {children} ──
    </div>
  );
}

function IndRow({ label, value, state, color, bar, barMax }) {
  return (
    <div style={{ marginBottom: 6, padding: "4px 0" }}>
      <div className="flex justify-between">
        <span style={{ fontSize: 10, color: C.textDim, letterSpacing: 1 }}>{label}</span>
        <span style={{ fontSize: 11, color: C.text, fontWeight: 500 }}>{value}</span>
      </div>
      <div className="flex justify-between mt-0.5">
        <span style={{ fontSize: 9, color }}>{state}</span>
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
  return (
    <div style={{ marginBottom: 6 }}>
      <div className="flex justify-between" style={{ marginBottom: 2 }}>
        <span style={{ fontSize: 10, color: C.textDim, letterSpacing: 1, fontWeight: weight || 400 }}>
          {label}
        </span>
        <span style={{ fontSize: 11, color, fontWeight: weight || 600 }}>{value}</span>
      </div>
      <div style={{ height: weight ? 6 : 4, background: C.border, position: "relative" }}>
        <div
          style={{
            height: "100%", width: `${value}%`, background: color,
            boxShadow: weight ? `0 0 6px ${color}` : "none",
            transition: "width .3s",
          }}
        />
      </div>
    </div>
  );
}

/* ----------  MODELS TAB  ---------- */
function ModelsTab({ scores, ens, sig, sigColor }) {
  if (!scores) return <Empty />;
  const data = [
    { name: "LSTM", value: scores.lstm, color: C.lstm,
      desc: "20-step recurrent · forget/input/output gates · tanh+sigmoid" },
    { name: "LogReg", value: scores.lr, color: C.lr,
      desc: "Sigmoid(weighted features) · RSI · MACD · momentum · BB · vol" },
    { name: "XGBoost", value: scores.xgb, color: C.xgb,
      desc: "3 decision stumps · trend / momentum / positioning · weighted" },
    { name: "Elman RNN", value: scores.rnn, color: C.rnn,
      desc: "15-step simple recurrent · single hidden state · tanh activation" },
  ];

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
      </div>

      <SectionLabel>MODEL COMPARISON</SectionLabel>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={data} margin={{ top: 10, right: 4, left: -28, bottom: 0 }}>
          <CartesianGrid stroke={C.grid} strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: C.textDim, fontSize: 9, fontFamily: FONT }} stroke={C.border} />
          <YAxis domain={[0, 100]} tick={{ fill: C.textDim, fontSize: 9, fontFamily: FONT }} stroke={C.border} />
          <Tooltip
            contentStyle={{ background: C.bgDeep, border: `1px solid ${C.borderHi}`, fontFamily: FONT, fontSize: 11, color: C.text }}
          />
          <ReferenceLine y={65} stroke={C.green} strokeDasharray="3 3" />
          <ReferenceLine y={35} stroke={C.red} strokeDasharray="3 3" />
          <Bar dataKey="value" radius={[2, 2, 0, 0]}>
            {data.map((d, i) => (
              <rect key={i} fill={d.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <SectionLabel style={{ marginTop: 14 }}>WEIGHTING</SectionLabel>
      {[
        { l: "LSTM", v: 30, c: C.lstm },
        { l: "LogReg", v: 25, c: C.lr },
        { l: "XGBoost", v: 25, c: C.xgb },
        { l: "RNN", v: 20, c: C.rnn },
      ].map((w) => (
        <div key={w.l} style={{ marginBottom: 4 }}>
          <div className="flex justify-between">
            <span style={{ fontSize: 10, color: w.c }}>{w.l}</span>
            <span style={{ fontSize: 10, color: C.textDim }}>{w.v}%</span>
          </div>
          <div style={{ height: 3, background: C.border }}>
            <div style={{ height: "100%", width: `${w.v * 3.33}%`, background: w.c }} />
          </div>
        </div>
      ))}

      <SectionLabel style={{ marginTop: 14 }}>ARCHITECTURE</SectionLabel>
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
          <div style={{ color: C.textDim, fontSize: 9, lineHeight: 1.4 }}>{d.desc}</div>
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
                  {r.name} {r.src === "SYN" && <span style={{ color: C.amber, marginLeft: 4 }}>SYN</span>}
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
            ◇ Click any row to load full chart · Synthetic data marked SYN
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
