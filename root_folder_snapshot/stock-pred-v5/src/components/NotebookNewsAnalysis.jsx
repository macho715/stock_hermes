import React from "react";
import { THEME } from "./DashboardCard";
function Chip({label,color}){return <span style={{fontSize:9,fontWeight:700,color:"#000",background:color,borderRadius:3,padding:"1px 5px",marginRight:3,letterSpacing:"0.03em"}}>{label}</span>;}
export default function NotebookNewsAnalysis({ analysis, compact=false }) {
  if(!analysis) return (
    <div style={{textAlign:"center",color:THEME.textMuted,fontSize:10,padding:compact?"8px 0":"16px"}}>
      <div style={{fontSize:16,marginBottom:4}}>📰</div>
      NotebookLM analysis unavailable<br/>
      <span style={{fontSize:9}}>뉴스 분석 데이터가 없습니다.</span>
    </div>
  );
  const bulls = analysis.bullish_factors||[];
  const bears = analysis.bearish_factors||[];
  const sentiment = analysis.sentiment||analysis.sentiment_score;
  const sc = typeof sentiment==="number"?sentiment:null;
  const sentColor = sc==null?THEME.textDim:sc>=0.2?THEME.green:sc<=-0.2?THEME.red:THEME.amber;
  return (
    <div>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:6}}>
        <span style={{fontSize:10,color:THEME.textMuted,textTransform:"uppercase",letterSpacing:"0.06em"}}>NotebookLM News</span>
        {sc!=null&&<span style={{fontSize:10,fontWeight:700,color:sentColor}}>
          {typeof analysis.sentiment==="string"?analysis.sentiment:`${sc>=0?"+":""}${(sc*100).toFixed(0)}%`}
        </span>}
      </div>
      {bulls.length>0&&<div style={{marginBottom:4}}>
        <div style={{fontSize:9,color:THEME.green,fontWeight:700,marginBottom:2}}>▲ BULLISH</div>
        {bulls.slice(0,compact?2:3).map((f,i)=><div key={i} style={{fontSize:9,color:THEME.textDim,paddingLeft:8,lineHeight:1.4}}>• {f}</div>)}
      </div>}
      {bears.length>0&&<div>
        <div style={{fontSize:9,color:THEME.red,fontWeight:700,marginBottom:2}}>▼ BEARISH</div>
        {bears.slice(0,compact?2:3).map((f,i)=><div key={i} style={{fontSize:9,color:THEME.textDim,paddingLeft:8,lineHeight:1.4}}>• {f}</div>)}
      </div>}
      {analysis.source_labels&&<div style={{marginTop:6,display:"flex",flexWrap:"wrap",gap:3}}>
        {analysis.source_labels.slice(0,4).map((l,i)=><Chip key={i} label={l} color={THEME.blue}/>)}
      </div>}
    </div>
  );
}
