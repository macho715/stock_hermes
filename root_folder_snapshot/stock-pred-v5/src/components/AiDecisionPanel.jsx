import React from "react";
import DashboardCard, { THEME } from "./DashboardCard";
import NotebookNewsAnalysis from "./NotebookNewsAnalysis";
import ActionPlanPanel from "./ActionPlanPanel";
const VERDICT_COLOR={ELIGIBLE_RECOMMENDATION:THEME.green,ACCUMULATE_RECOMMENDATION:THEME.green,AMBER_REVIEW_ONLY:THEME.amber,AMBER_WATCHLIST:THEME.amber,RED_NOT_RECOMMENDED:THEME.red,RED_DATA_INSUFFICIENT:THEME.red};
export default function AiDecisionPanel({ result }) {
  const score = result?.advisor_score;
  const rationale = result?.advisor_rationale || "AI rationale unavailable";
  const verdict = result?.verdict;
  const scoreColor = score==null?THEME.textDim:score>=0?THEME.green:THEME.red;
  const vColor = VERDICT_COLOR[verdict]||THEME.textDim;
  const nb = result?.notebook_analysis ?? null;
  return (
    <DashboardCard title="AI Decision Panel" subtitle="Powered by LLM + NotebookLM"
      style={{minHeight:448,display:"flex",flexDirection:"column",gap:0}}>
      {/* LLM Advisor row */}
      <div style={{padding:"10px 0",borderBottom:`1px solid rgba(40,64,87,0.45)`}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:6}}>
          <span style={{fontSize:10,color:THEME.textMuted,letterSpacing:"0.06em",textTransform:"uppercase"}}>LLM Advisor</span>
          <span style={{fontSize:10,fontWeight:800,color:vColor,letterSpacing:"0.04em"}}>{verdict?.replace(/_/g," ")}</span>
        </div>
        <div style={{position:"relative",height:6,background:"rgba(255,255,255,0.07)",borderRadius:3,marginBottom:6}}>
          <div style={{position:"absolute",left:"50%",top:0,width:1,height:"100%",background:"rgba(255,255,255,0.15)"}}/>
          {score!=null&&<div style={{position:"absolute",left:score>=0?"50%":`${(score+1)/2*100}%`,width:`${Math.abs(score)*50}%`,height:"100%",background:scoreColor,borderRadius:3,opacity:0.85}}/>}
        </div>
        <div style={{fontSize:11,color:scoreColor,fontWeight:700,textAlign:"right"}}>{score!=null?`${score>=0?"+":""}${Number(score).toFixed(2)}`:"—"}</div>
        <div style={{fontSize:10,color:THEME.textDim,lineHeight:1.5,marginTop:4,WebkitLineClamp:3,overflow:"hidden",display:"-webkit-box",WebkitBoxOrient:"vertical"}}>{rationale}</div>
      </div>
      {/* NotebookLM */}
      <div style={{padding:"8px 0",borderBottom:`1px solid rgba(40,64,87,0.45)`,flex:1}}>
        <NotebookNewsAnalysis analysis={nb} compact />
      </div>
      {/* Action Plan */}
      <div style={{padding:"8px 0"}}>
        <ActionPlanPanel result={result}/>
      </div>
    </DashboardCard>
  );
}
