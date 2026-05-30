import React from "react";
import { THEME, panelStyle, labelStyle } from "./DashboardCard";
export default function ConfidenceKpi({ confidence, label="Confidence", loading=false, safetyState=null }) {
  const rawPct = confidence!=null && Number(confidence) > 0
    ? Math.round(Number(confidence) > 1 ? Number(confidence) : Number(confidence)*100)
    : null;
  const blocked = Boolean(safetyState?.isHardBlocked);
  const pct = blocked ? safetyState.confidenceDisplayed : rawPct;
  const color = blocked ? THEME.red : pct==null?THEME.textDim:pct>=70?THEME.purple:pct>=50?THEME.amber:THEME.red;
  const valueText = loading ? "Loading" : blocked ? `≤${pct}%` : pct!=null ? `${pct}%` : "No data";
  const statusText = loading ? "Snapshot" : blocked ? "Blocked by risk gate" : pct==null ? "No data" : pct>=70 ? "High" : pct>=50 ? "Medium" : "Low";
  return (
    <section style={{...panelStyle,padding:"16px 20px",height:118,boxSizing:"border-box"}}>
      <div style={labelStyle}>{label}</div>
      <div style={{display:"grid",gridTemplateColumns:"120px 1fr",alignItems:"center",gap:20,marginTop:10}}>
      <div>
      <div style={{fontSize:34,fontWeight:900,color:THEME.text}} role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct||0}>
        {valueText}
      </div>
      <div style={{fontSize:13,color,marginTop:4,fontWeight:700}}>{statusText}</div>
      </div>
      <div style={{height:10,background:"rgba(255,255,255,0.08)",border:`1px solid ${THEME.border}`,borderRadius:999,overflow:"hidden"}}>
        <div style={{height:"100%",width:`${pct||0}%`,background:blocked?"linear-gradient(90deg,#ef4444,#ffb020)":"linear-gradient(90deg,#7132f5,#9b66ff)",borderRadius:999,transition:"width 0.5s",boxShadow:blocked?"0 0 14px rgba(239,68,68,0.35)":"0 0 14px rgba(113,50,245,0.45)"}}/>
      </div>
      </div>
    </section>
  );
}
