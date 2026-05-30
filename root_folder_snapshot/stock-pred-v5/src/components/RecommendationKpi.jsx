import React from "react";
import { THEME, panelStyle, labelStyle } from "./DashboardCard";
export default function RecommendationKpi({ verdict, advisorScore, safetyState=null }) {
  const labelFromVerdict = verdict
    ? String(verdict).includes("RED") ? "SELL" : String(verdict).includes("AMBER") ? "HOLD" : "BUY"
    : null;
  const baseLabel = advisorScore == null && !labelFromVerdict ? "NO DATA" : advisorScore == null ? labelFromVerdict : advisorScore >= 0 ? "BUY" : "SELL";
  const blocked = Boolean(safetyState?.isHardBlocked);
  const label = blocked ? safetyState.uiVerdict : baseLabel;
  const scoreColor = blocked ? THEME.red : advisorScore==null?THEME.textDim:advisorScore>=0?THEME.green:THEME.red;
  return (
    <section style={{...panelStyle,padding:"16px 20px",height:118,boxSizing:"border-box",position:"relative"}}>
      <div style={labelStyle}>AI Recommendation</div>
      <div style={{fontSize:blocked?21:30,fontWeight:900,color:scoreColor,letterSpacing:"0.02em",lineHeight:1.08,marginTop:10,maxWidth:220}}>{label}</div>
      {blocked ? (
        <div style={{fontSize:11,color:THEME.amber,marginTop:5,fontWeight:800}}>
          Original AI Rec: {safetyState.originalRecommendation || baseLabel}
        </div>
      ) : advisorScore!=null&&<div style={{fontSize:11,color:scoreColor,marginTop:4,fontWeight:700}}>
        ↗ {advisorScore>=0?"Bullish Bias":"Bearish Bias"}
      </div>}
      <div style={{position:"absolute",right:34,top:26,width:70,height:70,border:`2px solid ${THEME.purple}`,borderRadius:"50%",display:"grid",placeItems:"center",boxShadow:"0 0 20px rgba(113,50,245,0.22)"}}>
        <span style={{fontSize:blocked?34:38,color:blocked?THEME.red:THEME.purple,fontWeight:900}}>{blocked ? "⊘" : "↗"}</span>
      </div>
    </section>
  );
}
