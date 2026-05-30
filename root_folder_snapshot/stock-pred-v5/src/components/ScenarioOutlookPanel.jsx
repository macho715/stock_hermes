import React from "react";
import DashboardCard, { THEME } from "./DashboardCard";
function ScenarioCard({label,data,color}){
  if(!data) return null;
  const prob = data.probability!=null?Math.round(data.probability*100):null;
  return (
    <div style={{background:"rgba(255,255,255,0.025)",border:`1px solid ${color}33`,borderRadius:6,padding:"8px 10px"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:4}}>
        <span style={{fontSize:10,fontWeight:800,color,letterSpacing:"0.05em",textTransform:"uppercase"}}>{label}</span>
        {prob!=null&&<span style={{fontSize:9,color:THEME.textMuted}}>{prob}%</span>}
      </div>
      <div style={{fontSize:11,fontWeight:700,color:THEME.text}}>{data.range||"—"}</div>
      <div style={{fontSize:10,color,fontWeight:600}}>{data.return||"—"}</div>
      {prob!=null&&<div style={{marginTop:6,height:3,background:"rgba(255,255,255,0.07)",borderRadius:2}}>
        <div style={{height:"100%",width:`${prob}%`,background:color,borderRadius:2}}/>
      </div>}
    </div>
  );
}
export default function ScenarioOutlookPanel({ scenario }) {
  if(!scenario) return <DashboardCard title="Scenario Outlook"><div style={{color:THEME.textMuted,fontSize:10,textAlign:"center",padding:8}}>Scenario data unavailable</div></DashboardCard>;
  return (
    <DashboardCard title="Scenario Outlook">
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:8}}>
        <ScenarioCard label="Bull" data={scenario.bull} color={THEME.green}/>
        <ScenarioCard label="Base" data={scenario.base} color={THEME.amber}/>
        <ScenarioCard label="Bear" data={scenario.bear} color={THEME.red}/>
      </div>
      <div style={{fontSize:8,color:THEME.textMuted,marginTop:6,textAlign:"center"}}>
        Report-only · Manual review required · No broker execution
      </div>
    </DashboardCard>
  );
}
