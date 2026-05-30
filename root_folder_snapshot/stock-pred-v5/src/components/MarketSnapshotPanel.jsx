import React from "react";
import DashboardCard, { THEME } from "./DashboardCard";

function formatNumber(value, digits = 2, fallback = "No data") {
  if (value == null || !Number.isFinite(Number(value))) return fallback;
  return Number(value).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatCompact(value, fallback = "No data") {
  if (value == null || !Number.isFinite(Number(value))) return fallback;
  return Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 }).format(Number(value));
}

function pct(current, previous) {
  if (!Number.isFinite(Number(current)) || !Number.isFinite(Number(previous)) || Number(previous) === 0) return null;
  return ((Number(current) - Number(previous)) / Number(previous)) * 100;
}

function Row({ label, value, delta, note = "Actual", fallback = "No data" }) {
  const hasDelta = delta != null && Number.isFinite(Number(delta));
  const color = !hasDelta ? THEME.textMuted : delta >= 0 ? THEME.greenBright : THEME.red;
  return (
    <div style={{display:"grid",gridTemplateColumns:"1.2fr 1fr 0.8fr",alignItems:"center",minHeight:26,borderBottom:`1px solid ${THEME.border}`}}>
      <span style={{fontSize:12,color:THEME.textDim}}>{label}</span>
      <span style={{fontSize:12,fontWeight:500,color:THEME.text}}>{value || fallback}</span>
      <span style={{fontSize:12,fontWeight:800,color,textAlign:"right"}}>{hasDelta ? `${delta >= 0 ? "+" : ""}${delta.toFixed(2)}%` : note}</span>
    </div>
  );
}

export default function MarketSnapshotPanel({ result, ohlcvRecords=[], loading=false }) {
  const rows = Array.isArray(ohlcvRecords) ? ohlcvRecords.filter((d)=>Number.isFinite(Number(d.close))) : [];
  const last = rows.at(-1) || null;
  const prev = rows.at(-2) || null;
  const last20 = rows.slice(-20);
  const last252 = rows.slice(-252);
  const avgVol20 = last20.length
    ? last20.reduce((sum,d)=>sum + (Number(d.volume) || 0),0) / last20.length
    : null;
  const rangeLow = last252.length ? Math.min(...last252.map((d)=>Number(d.low ?? d.close)).filter(Number.isFinite)) : null;
  const rangeHigh = last252.length ? Math.max(...last252.map((d)=>Number(d.high ?? d.close)).filter(Number.isFinite)) : null;
  const rangePct = last && rangeLow != null && rangeHigh != null && rangeHigh > rangeLow
    ? Math.max(0, Math.min(100, ((Number(last.close)-rangeLow)/(rangeHigh-rangeLow))*100))
    : null;
  const marketCap = result?.market_cap ?? result?.fundamentals?.market_cap ?? null;
  const pe = result?.pe_ttm ?? result?.fundamentals?.pe_ttm ?? null;
  const eps = result?.eps_ttm ?? result?.fundamentals?.eps_ttm ?? null;
  const dividendYield = result?.dividend_yield ?? result?.fundamentals?.dividend_yield ?? null;
  const sector = result?.sector ?? result?.fundamentals?.sector ?? null;
  const industry = result?.industry ?? result?.fundamentals?.industry ?? null;
  const fundamentalFallback = loading ? "Loading" : "No data";

  return (
    <DashboardCard title="Market Snapshot">
      <Row label="Open" value={formatNumber(last?.open)} delta={pct(last?.open, prev?.close)}/>
      <Row label="High" value={formatNumber(last?.high)} delta={pct(last?.high, prev?.close)}/>
      <Row label="Low" value={formatNumber(last?.low)} delta={pct(last?.low, prev?.close)}/>
      <Row label="Close (Prev)" value={formatNumber(prev?.close)} delta={pct(last?.close, prev?.close)}/>
      <Row label="Volume" value={formatCompact(last?.volume)} delta={pct(last?.volume, avgVol20)}/>
      <Row label="Avg Vol (20D)" value={formatCompact(avgVol20)} note="20D"/>
      <Row label="Market Cap" value={formatCompact(marketCap, fundamentalFallback)} note="YF"/>
      <Row label="PE (TTM)" value={formatNumber(pe, 2, fundamentalFallback)} note="YF"/>
      <Row label="EPS (TTM)" value={formatNumber(eps, 2, fundamentalFallback)} note="YF"/>
      <Row label="Div Yield" value={dividendYield!=null ? `${formatNumber(Number(dividendYield) > 1 ? Number(dividendYield) : Number(dividendYield)*100)}%` : fundamentalFallback} note="YF"/>
      <div style={{display:"grid",gridTemplateColumns:"1.2fr 1fr 0.8fr",alignItems:"center",minHeight:28,borderBottom:`1px solid ${THEME.border}`}}>
        <span style={{fontSize:12,color:THEME.textDim}}>52W Range</span>
        <div style={{height:5,background:"rgba(255,255,255,0.09)",borderRadius:999,position:"relative"}}>
          {rangePct!=null&&<div style={{position:"absolute",left:`${rangePct}%`,top:-4,width:6,height:13,borderRadius:3,background:"#fff",boxShadow:"0 0 12px rgba(113,50,245,0.8)"}}/>}
          {rangePct!=null&&<div style={{height:"100%",width:`${rangePct}%`,background:THEME.purple,borderRadius:999}}/>}
        </div>
        <span style={{fontSize:10,color:THEME.textMuted,textAlign:"right"}}>{rangeHigh!=null ? formatNumber(rangeHigh) : "No data"}</span>
      </div>
      <Row label="Sector" value={sector || fundamentalFallback} note="YF"/>
      <Row label="Industry" value={industry || fundamentalFallback} note="YF"/>
    </DashboardCard>
  );
}
