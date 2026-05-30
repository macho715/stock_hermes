import React from "react";
import { THEME } from "./DashboardCard";
function displayText(value) {
  return String(value || "").replace(/\u2014/g, "-");
}
function Row({dot,title,source,time,color}){return <div style={{display:"grid",gridTemplateColumns:"14px 1fr 96px 92px",alignItems:"center",minHeight:24,borderBottom:`1px solid ${THEME.border}`}}>
  <span style={{width:8,height:8,borderRadius:"50%",background:color,display:"inline-block"}}/>
  <span style={{fontSize:11,color:THEME.textDim,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{displayText(title)}</span>
  <span style={{fontSize:10,color:THEME.textMuted,textAlign:"right"}}>{source}</span>
  <span style={{fontSize:10,color:THEME.textMuted,textAlign:"right"}}>{time}</span>
</div>;}
export default function NotebookNewsAnalysis({ analysis, headlines=[], compact=false }) {
  const headlineRows = Array.isArray(headlines) ? headlines.slice(0,5) : [];
  const sourceLabel = analysis?.analysis_source === "openai_api"
    ? `OpenAI${analysis?.openai_model ? ` ${analysis.openai_model}` : ""}`
    : analysis?.analysis_source === "notelm_fallback" ? "Notelm Fallback" : "NotebookLM";
  if(!analysis) return (
    <div>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:4}}>
        <span style={{fontSize:13,color:THEME.text,fontWeight:900,textTransform:"uppercase"}}>NotebookLM News Analysis <span style={{fontSize:11,color:THEME.textMuted,fontWeight:600}}>(Past 72h)</span></span>
        <span style={{fontSize:11,color:headlineRows.length?THEME.greenBright:THEME.textMuted}}>{headlineRows.length ? `YFinance ${headlineRows.length}` : "Unavailable"}</span>
      </div>
      {headlineRows.length ? (
        headlineRows.map((h,i)=><Row key={`${h.title}-${i}`} title={h.title} source={h.source || "YFinance"} time={(h.published_at || "").slice(0,10)} color={i < 3 ? THEME.green : THEME.textMuted}/>)
      ) : (
        <div style={{fontSize:11,color:THEME.textMuted,padding:"18px 0",textAlign:"center",border:`1px dashed ${THEME.border}`,borderRadius:6}}>
          No news data returned by the current snapshot.
        </div>
      )}
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
        <span style={{fontSize:13,color:THEME.text,fontWeight:900,textTransform:"uppercase"}}>{sourceLabel} News Analysis <span style={{fontSize:11,color:THEME.textMuted,fontWeight:600}}>(Past 72h)</span></span>
        {sc!=null&&<span style={{fontSize:10,fontWeight:700,color:sentColor}}>
          {typeof analysis.sentiment==="string"?analysis.sentiment:`${sc>=0?"+":""}${(sc*100).toFixed(0)}%`}
        </span>}
      </div>
      {[...bulls.slice(0,3),...bears.slice(0,2)].slice(0,5).map((f,i)=><Row key={i} title={f} source={analysis.source_labels?.[i]||sourceLabel} time={analysis.as_of||analysis.generated_at||""} color={i<3?THEME.green:THEME.red}/>)}
      {bulls.length===0&&bears.length===0&&(
        <div style={{fontSize:11,color:THEME.textMuted,padding:"18px 0",textAlign:"center",border:`1px dashed ${THEME.border}`,borderRadius:6}}>
          NotebookLM analysis contains no bullish or bearish factor rows.
        </div>
      )}
    </div>
  );
}
