import React from "react";
import { THEME } from "./DashboardCard";
const VERDICT_COLOR = {
  ELIGIBLE_RECOMMENDATION:THEME.green,ACCUMULATE_RECOMMENDATION:THEME.green,
  AMBER_REVIEW_ONLY:THEME.amber,AMBER_WATCHLIST:THEME.amber,
  RED_NOT_RECOMMENDED:THEME.red,RED_DATA_INSUFFICIENT:THEME.red,
};
export default function RecommendationKpi({ verdict, advisorScore }) {
  const color = VERDICT_COLOR[verdict] || THEME.textDim;
  const label = verdict ? verdict.replace(/_/g," ").replace("RECOMMENDATION","REC") : "—";
  const scoreColor = advisorScore==null?THEME.textDim:advisorScore>=0?THEME.green:THEME.red;
  return (
    <section style={{background:"linear-gradient(180deg,rgba(12,28,48,0.94),rgba(6,15,28,0.94))",border:`1px solid ${THEME.border}`,borderRadius:8,padding:"14px 16px",boxShadow:"0 4px 16px rgba(0,0,0,0.24)"}}>
      <div style={{fontSize:10,color:THEME.textMuted,letterSpacing:"0.07em",textTransform:"uppercase",marginBottom:6}}>AI Recommendation</div>
      <div style={{fontSize:13,fontWeight:800,color,letterSpacing:"0.04em",lineHeight:1.3}}>{label}</div>
      {advisorScore!=null&&<div style={{fontSize:11,color:scoreColor,marginTop:4,fontWeight:700}}>
        LLM {advisorScore>=0?"+":""}{Number(advisorScore).toFixed(2)}
      </div>}
    </section>
  );
}
