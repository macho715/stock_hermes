import React from "react";
import DashboardCard, { THEME } from "./DashboardCard";
export default function ModelScoresPanel({ modelEvidence }) {
  const models = modelEvidence ? Object.entries(modelEvidence).filter(([,v])=>v!=null&&v?.score!=null) : [];
  return (
    <DashboardCard title="Model Scores" style={{height:160}}>
      {models.length===0 ? (
        <div style={{color:THEME.textMuted,fontSize:11,textAlign:"center",paddingTop:16}}>Backend evidence unavailable</div>
      ) : (
        <div style={{display:"grid",gridTemplateColumns:`repeat(${Math.min(models.length,4)},1fr)`,gap:8}}>
          {models.map(([name,v])=>{
            const s=Number(v.score||0);
            const c=s>=56?THEME.green:s>=45?THEME.amber:THEME.red;
            return <div key={name} style={{textAlign:"center"}}>
              <div style={{fontSize:9,color:THEME.textMuted,textTransform:"uppercase",letterSpacing:"0.05em"}}>{name}</div>
              <div style={{fontSize:18,fontWeight:800,color:c}}>{s.toFixed(0)}</div>
            </div>;
          })}
        </div>
      )}
    </DashboardCard>
  );
}
