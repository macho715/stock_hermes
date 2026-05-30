import React from "react";
import { THEME } from "./DashboardCard";
export default function RiskRewardKpi({ riskReward }) {
  const rr = riskReward!=null?Number(riskReward):null;
  const color = rr==null?THEME.textDim:rr>=2.5?THEME.green:rr>=1.5?THEME.amber:THEME.red;
  const label = rr==null?"—":rr>=2.5?"Attractive":rr>=1.5?"Neutral":"Poor";
  return (
    <section style={{background:"linear-gradient(180deg,rgba(12,28,48,0.94),rgba(6,15,28,0.94))",border:`1px solid ${THEME.border}`,borderRadius:8,padding:"14px 16px",boxShadow:"0 4px 16px rgba(0,0,0,0.24)"}}>
      <div style={{fontSize:10,color:THEME.textMuted,letterSpacing:"0.07em",textTransform:"uppercase",marginBottom:6}}>Risk / Reward</div>
      <div style={{fontSize:26,fontWeight:800,color}}>{rr!=null?`${rr.toFixed(1)}×`:"—"}</div>
      <div style={{fontSize:11,color,marginTop:4,fontWeight:600}}>{label}</div>
    </section>
  );
}
