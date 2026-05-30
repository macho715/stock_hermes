import React from "react";
import { THEME } from "./DashboardCard";
export default function ConfidenceKpi({ confidence, label="Confidence" }) {
  const pct = confidence!=null ? Math.round(confidence*100) : null;
  const color = pct==null?THEME.textDim:pct>=70?THEME.green:pct>=50?THEME.amber:THEME.red;
  return (
    <section style={{background:"linear-gradient(180deg,rgba(12,28,48,0.94),rgba(6,15,28,0.94))",border:`1px solid ${THEME.border}`,borderRadius:8,padding:"14px 16px",boxShadow:"0 4px 16px rgba(0,0,0,0.24)"}}>
      <div style={{fontSize:10,color:THEME.textMuted,letterSpacing:"0.07em",textTransform:"uppercase",marginBottom:6}}>{label}</div>
      <div style={{fontSize:26,fontWeight:800,color}} role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct||0}>
        {pct!=null?`${pct}%`:"—"}
      </div>
      <div style={{marginTop:8,height:4,background:"rgba(255,255,255,0.07)",borderRadius:2}}>
        <div style={{height:"100%",width:`${pct||0}%`,background:color,borderRadius:2,transition:"width 0.5s"}}/>
      </div>
      <div style={{fontSize:10,color:THEME.textDim,marginTop:4}}>{pct==null?"No data":pct>=70?"High":pct>=50?"Medium":"Low"}</div>
    </section>
  );
}
