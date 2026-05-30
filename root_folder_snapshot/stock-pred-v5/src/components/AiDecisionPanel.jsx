import React from "react";
import DashboardCard, { THEME } from "./DashboardCard";
import NotebookNewsAnalysis from "./NotebookNewsAnalysis";
import ActionPlanPanel from "./ActionPlanPanel";
const VERDICT_COLOR={ELIGIBLE_RECOMMENDATION:THEME.green,ACCUMULATE_RECOMMENDATION:THEME.green,AMBER_REVIEW_ONLY:THEME.amber,AMBER_WATCHLIST:THEME.amber,RED_NOT_RECOMMENDED:THEME.red,RED_DATA_INSUFFICIENT:THEME.red};
function labelFromVerdict(verdict, score) {
  if (score != null) return score >= 0 ? "BUY" : "SELL";
  if (!verdict) return "PENDING";
  const text = String(verdict);
  if (text.includes("RED")) return "SELL";
  if (text.includes("AMBER")) return "HOLD";
  return "BUY";
}

export default function AiDecisionPanel({ result, headlines=[], loading=false, ticker="" }) {
  if (loading || !result) {
    const tickerLabel = ticker || "selected ticker";
    return (
      <DashboardCard title="AI Decision Panel" subtitle="Powered by LLM + NotebookLM"
        right={<span style={{fontSize:11,color:THEME.textMuted,fontWeight:800}}>VERDICT</span>}
        style={{minHeight:448,display:"flex",flexDirection:"column",gap:0}}>
        <div style={{padding:"8px 0 10px",borderBottom:`1px solid ${THEME.border}`}}>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:6}}>
            <span style={{fontSize:12,color:THEME.textDim,letterSpacing:"0.04em",textTransform:"uppercase",fontWeight:800}}>LLM Advisor <span style={{fontSize:10,fontWeight:500}}>(loading) ⓘ</span></span>
          </div>
          <div style={{display:"grid",gridTemplateColumns:"190px 1fr",border:`1px solid ${THEME.purple}66`,borderRadius:6,overflow:"hidden",background:"linear-gradient(90deg,rgba(113,50,245,0.28),rgba(113,50,245,0.06))"}}>
            <div style={{fontSize:28,fontWeight:900,color:"#fff",background:"linear-gradient(90deg,#7132f5,#4d1db6)",padding:"10px 18px"}}>PENDING</div>
            <div style={{fontSize:12,color:THEME.text,lineHeight:1.45,padding:"10px 16px"}}>Loading AI analysis for {tickerLabel}. Current ticker data will appear when the new snapshot is ready.</div>
          </div>
        </div>
        <div style={{padding:"8px 0",borderBottom:`1px solid ${THEME.border}`,flex:1}}>
          <div style={{height:"100%",minHeight:116,border:`1px dashed ${THEME.purple}55`,borderRadius:6,display:"grid",placeItems:"center",background:"rgba(113,50,245,0.05)",color:THEME.textMuted,fontSize:12,fontWeight:700}}>
            Waiting for current ticker OpenAI/Notebook analysis.
          </div>
        </div>
        <div style={{padding:"8px 0"}}>
          <div style={{border:`1px solid ${THEME.border}`,borderRadius:6,overflow:"hidden",fontSize:12}}>
            {["ENTRY", "STOP LOSS", "TAKE PROFIT 1"].map(label => (
              <div key={label} style={{display:"grid",gridTemplateColumns:"1fr 1fr",padding:"6px 10px",borderBottom:label==="TAKE PROFIT 1"?"none":`1px solid ${THEME.border}`,color:THEME.textDim}}>
                <b>{label}</b>
                <span style={{textAlign:"right",color:THEME.textMuted}}>Loading</span>
              </div>
            ))}
          </div>
        </div>
      </DashboardCard>
    );
  }
  const score = result?.advisor_score;
  const rationale = result?.advisor_rationale
    || (Array.isArray(result?.reasons) && result.reasons.length ? result.reasons.slice(0,3).join("; ") : "")
    || result?.candidate_label
    || "Recommendation snapshot is loading.";
  const verdict = result?.verdict;
  const scoreColor = score==null?THEME.textDim:score>=0?THEME.green:THEME.red;
  const vColor = VERDICT_COLOR[verdict]||THEME.textDim;
  const nb = result?.notebook_analysis ?? null;
  return (
    <DashboardCard title="AI Decision Panel" subtitle="Powered by LLM + NotebookLM"
      right={<span style={{fontSize:11,color:THEME.textMuted,fontWeight:800}}>VERDICT</span>}
      style={{minHeight:448,display:"flex",flexDirection:"column",gap:0}}>
      {/* LLM Advisor row */}
      <div style={{padding:"8px 0 10px",borderBottom:`1px solid ${THEME.border}`}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:6}}>
          <span style={{fontSize:12,color:THEME.textDim,letterSpacing:"0.04em",textTransform:"uppercase",fontWeight:800}}>LLM Advisor <span style={{fontSize:10,fontWeight:500}}>(GPT-4o) ⓘ</span></span>
        </div>
        <div style={{display:"grid",gridTemplateColumns:"190px 1fr",border:`1px solid ${THEME.green}66`,borderRadius:6,overflow:"hidden",background:"linear-gradient(90deg,rgba(20,158,97,0.4),rgba(20,158,97,0.08))"}}>
          <div style={{fontSize:30,fontWeight:900,color:"#fff",background:"linear-gradient(90deg,#149e61,#0b6d3b)",padding:"10px 18px"}}>{labelFromVerdict(verdict, score)}</div>
          <div style={{fontSize:12,color:THEME.text,lineHeight:1.45,padding:"10px 16px"}}>{rationale}</div>
        </div>
      </div>
      {/* NotebookLM */}
      <div style={{padding:"8px 0",borderBottom:`1px solid ${THEME.border}`,flex:1}}>
        <NotebookNewsAnalysis analysis={nb} headlines={headlines} compact />
      </div>
      {/* Action Plan */}
      <div style={{padding:"8px 0"}}>
        <ActionPlanPanel result={result}/>
      </div>
    </DashboardCard>
  );
}
