import React from "react";
import { THEME, panelStyle, labelStyle } from "./DashboardCard";
export default function RiskRewardKpi({ riskReward, loading=false, safetyState=null }) {
  const raw = riskReward!=null?Number(riskReward):null;
  const rr = raw && raw > 0 ? raw : null;
  const blocked = Boolean(safetyState?.isHardBlocked);
  const color = blocked?THEME.red:rr==null?THEME.textDim:rr>=2.5?THEME.green:rr>=1.5?THEME.amber:THEME.red;
  const label = loading ? "Loading" : blocked ? "Risk gate" : rr==null ? "No data" : rr>=2.5 ? "Attractive" : rr>=1.5 ? "Neutral" : "Poor";
  return (
    <section style={{...panelStyle,padding:"16px 20px",height:118,boxSizing:"border-box",display:"grid",gridTemplateColumns:"1fr 130px",gap:18}}>
      <div>
        <div style={labelStyle}>Risk / Reward (TP1)</div>
        <div style={{fontSize:blocked?29:32,fontWeight:900,color,marginTop:12}}>{loading ? "Loading" : blocked ? "No trade" : rr!=null ? `${rr.toFixed(2)} : 1` : "No data"}</div>
        <div style={{fontSize:12,color,marginTop:4,fontWeight:700}}>{label==="Attractive"?"Good":label}</div>
      </div>
      <div style={{display:"flex",alignItems:"end",justifyContent:"center",gap:20,paddingBottom:4}}>
        <div style={{textAlign:"center"}}>
          <div style={{width:34,height:18,borderRadius:4,background:"linear-gradient(180deg,#ff4d57,#ef4444)",boxShadow:"0 0 12px rgba(239,68,68,0.34)",opacity:rr==null&&!blocked?0.25:1}}/>
          <div style={{fontSize:10,color:THEME.red,fontWeight:800,marginTop:6}}>RISK</div>
        </div>
        <div style={{textAlign:"center"}}>
          <div style={{width:38,height:62,borderRadius:4,background:"linear-gradient(180deg,#27d27d,#149e61)",boxShadow:"0 0 14px rgba(20,158,97,0.35)",opacity:blocked||rr==null?0.25:1}}/>
          <div style={{fontSize:10,color:THEME.greenBright,fontWeight:800,marginTop:6}}>REWARD</div>
        </div>
      </div>
    </section>
  );
}
