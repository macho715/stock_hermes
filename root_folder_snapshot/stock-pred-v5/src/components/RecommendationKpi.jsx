import React from "react";
import { THEME, panelStyle, labelStyle } from "./DashboardCard";
const VERDICT_COLOR = {
  ELIGIBLE_RECOMMENDATION:THEME.green,ACCUMULATE_RECOMMENDATION:THEME.green,
  AMBER_REVIEW_ONLY:THEME.amber,AMBER_WATCHLIST:THEME.amber,
  RED_NOT_RECOMMENDED:THEME.red,RED_DATA_INSUFFICIENT:THEME.red,
};
export default function RecommendationKpi({ verdict, advisorScore }) {
  const color = VERDICT_COLOR[verdict] || THEME.textDim;
  const labelFromVerdict = verdict
    ? String(verdict).includes("RED") ? "SELL" : String(verdict).includes("AMBER") ? "HOLD" : "BUY"
    : null;
  const label = advisorScore == null && !labelFromVerdict ? "NO DATA" : advisorScore == null ? labelFromVerdict : advisorScore >= 0 ? "BUY" : "SELL";
  const scoreColor = advisorScore==null?THEME.textDim:advisorScore>=0?THEME.green:THEME.red;
  return (
    <section style={{...panelStyle,padding:"16px 20px",height:118,boxSizing:"border-box",position:"relative"}}>
      <div style={labelStyle}>AI Recommendation</div>
      <div style={{fontSize:30,fontWeight:900,color:scoreColor,letterSpacing:"0.02em",lineHeight:1.1,marginTop:10}}>{label}</div>
      {advisorScore!=null&&<div style={{fontSize:11,color:scoreColor,marginTop:4,fontWeight:700}}>
        ↗ {advisorScore>=0?"Bullish Bias":"Bearish Bias"}
      </div>}
      <div style={{position:"absolute",right:34,top:26,width:70,height:70,border:`2px solid ${THEME.purple}`,borderRadius:"50%",display:"grid",placeItems:"center",boxShadow:"0 0 20px rgba(113,50,245,0.22)"}}>
        <span style={{fontSize:38,color:THEME.purple,fontWeight:900}}>↗</span>
      </div>
    </section>
  );
}
