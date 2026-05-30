import React from "react";
import DashboardCard, { THEME } from "./DashboardCard";
export default function WatchlistPanel({ symbols=[], selected, onSelect }) {
  const rows = Array.isArray(symbols) ? symbols : [];
  return (
    <DashboardCard title="Watchlist" right={<span style={{fontSize:11,color:THEME.textMuted}}>View All</span>} style={{height:"100%"}}>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 0.7fr 0.9fr 0.8fr",fontSize:10,color:THEME.textMuted,borderBottom:`1px solid ${THEME.border}`,paddingBottom:6}}>
        <span>Ticker</span><span>Price</span><span>Chg %</span><span>AI Rec</span><span>Confidence</span>
      </div>
      <div style={{overflowY:"auto",maxHeight:150}}>
        {rows.length===0&&(
          <div style={{fontSize:11,color:THEME.textMuted,padding:"42px 0",textAlign:"center",border:`1px dashed ${THEME.border}`,borderRadius:6}}>
            No watchlist symbols returned by the current universe source.
          </div>
        )}
        {rows.map(s=>{
          const isSelected = s.symbol===selected;
          const hasChange = s.changePct != null && Number.isFinite(Number(s.changePct));
          const up = hasChange ? Number(s.changePct) >= 0 : true;
          const rec = s.rec || "—";
          const recColor = rec==="NO TRADE"||rec==="SELL"?THEME.red:rec==="HOLD"?THEME.amber:rec==="BUY"?THEME.greenBright:THEME.textMuted;
          const confidence = s.confidence!=null ? Number(s.confidence) : null;
          const confidencePct = confidence!=null && Number.isFinite(confidence)
            ? Math.round(confidence > 1 ? confidence : confidence * 100)
            : null;
          const analysisSource = s.notebookAnalysis?.analysis_source || "";
          const rowTitle = analysisSource
            ? `${s.symbol} ${analysisSource} · news ${s.newsCount || 0} · ${s.priceProvider || "price source unavailable"} ${s.priceAsOf || ""}`
            : `${s.symbol} · ${s.priceProvider || "price source unavailable"} ${s.priceAsOf || ""}`;
          return (
            <div key={s.symbol} onClick={()=>onSelect?.(s.symbol)}
              title={rowTitle}
              style={{display:"grid",gridTemplateColumns:"1fr 1fr 0.7fr 0.9fr 0.8fr",alignItems:"center",
                minHeight:28,cursor:"pointer",borderBottom:`1px solid ${THEME.border}`,
                background:isSelected?THEME.purpleSoft:"transparent",boxShadow:isSelected?`inset 3px 0 0 ${THEME.purple}`:"none"}}>
              <span style={{fontSize:12,fontWeight:800,color:isSelected?THEME.text:THEME.textDim,paddingLeft:8}}>{s.symbol}</span>
              <span style={{fontSize:12,color:THEME.text}}>{typeof s.price==="number"?s.price.toFixed(2):s.price||"—"}</span>
              <span style={{fontSize:12,color:hasChange?(up?THEME.greenBright:THEME.red):THEME.textMuted}}>{hasChange?`${up?"+":""}${Number(s.changePct).toFixed(2)}%`:"—"}</span>
              <span style={{fontSize:12,fontWeight:900,color:recColor}}>{rec}</span>
              <span style={{fontSize:12,color:confidencePct!=null?THEME.purple:THEME.textMuted}}>{confidencePct!=null?`${confidencePct}%`:"—"}</span>
            </div>
          );
        })}
      </div>
    </DashboardCard>
  );
}
