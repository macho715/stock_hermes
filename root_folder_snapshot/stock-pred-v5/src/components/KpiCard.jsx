import React from "react";
import { THEME } from "./DashboardCard";
export default function KpiCard({ label, value, sub, accent, icon, style={} }) {
  const color = accent || THEME.cyan;
  return (
    <section style={{
      background:"linear-gradient(180deg,rgba(12,28,48,0.94),rgba(6,15,28,0.94))",
      border:`1px solid ${THEME.border}`,borderRadius:8,padding:"14px 16px",
      boxShadow:"0 4px 16px rgba(0,0,0,0.24)",...style
    }}>
      <div style={{fontSize:10,color:THEME.textMuted,letterSpacing:"0.07em",textTransform:"uppercase",marginBottom:6}}>
        {icon&&<span style={{marginRight:5}}>{icon}</span>}{label}
      </div>
      <div style={{fontSize:26,fontWeight:800,color,lineHeight:1.15,wordBreak:"break-all"}} aria-label={label}>
        {value??<span style={{color:THEME.textMuted}}>—</span>}
      </div>
      {sub&&<div style={{fontSize:11,color:THEME.textDim,marginTop:4}}>{sub}</div>}
    </section>
  );
}
