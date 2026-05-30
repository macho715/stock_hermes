import React from "react";
import DashboardCard, { THEME } from "./DashboardCard";
function ScenarioCard({label,data,color}){
  if(!data) return null;
  const prob = data.probability!=null?Math.round(data.probability*100):null;
  return (
    <div style={{background:`linear-gradient(180deg,${color}18,rgba(255,255,255,0.015))`,border:`1px solid ${color}88`,borderRadius:10,padding:"14px 18px",minHeight:132}}>
      <div style={{textAlign:"center",marginBottom:8}}>
        <div style={{fontSize:12,fontWeight:900,color,letterSpacing:"0.04em",textTransform:"uppercase"}}>{label} Case</div>
        <div style={{fontSize:24,fontWeight:900,color:THEME.text}}>{data.range||"—"}</div>
        <div style={{fontSize:14,color,fontWeight:800}}>{data.return||"—"}</div>
        {prob!=null&&<div style={{fontSize:12,color:THEME.textDim,marginTop:5}}>Probability <span style={{color,fontWeight:900}}>{prob}%</span></div>}
      </div>
      {(data.drivers||[]).slice(0,3).map((d,i)=><div key={i} style={{fontSize:11,color:THEME.textDim,lineHeight:1.5}}>• {d}</div>)}
      {(!data.drivers||data.drivers.length===0)&&<div style={{fontSize:11,color:THEME.textMuted,lineHeight:1.5}}>No scenario drivers supplied.</div>}
    </div>
  );
}
export default function ScenarioOutlookPanel({ scenario }) {
  const data = scenario || null;
  return (
    <DashboardCard title="Scenario Outlook" subtitle="Next 4 Weeks" style={{height:"100%"}}>
      {!data?(
        <div style={{fontSize:11,color:THEME.textMuted,padding:"58px 0",textAlign:"center",border:`1px dashed ${THEME.border}`,borderRadius:6}}>
          Scenario data unavailable in the current recommendation snapshot.
        </div>
      ):(
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:10}}>
          <ScenarioCard label="Bull" data={data.bull} color={THEME.greenBright}/>
          <ScenarioCard label="Base" data={data.base} color={THEME.textDim}/>
          <ScenarioCard label="Bear" data={data.bear} color={THEME.red}/>
        </div>
      )}
      <div style={{fontSize:10,color:THEME.textMuted,marginTop:8}}>
        All scenarios are model estimates and for reference only.
      </div>
    </DashboardCard>
  );
}
