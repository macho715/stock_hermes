import React from "react";
import DashboardCard, { THEME } from "./DashboardCard";

function collectScores(modelEvidence) {
  if (!modelEvidence || modelEvidence.status !== "PASS") return [];
  const raw = modelEvidence.model_scores || {};
  const entries = [
    ["Overall", modelEvidence.ensemble_score ?? raw.main],
    ["Logistic", raw.logistic],
    ["XGBoost", raw.xgboost],
    ["LSTM", raw.lstm],
    ["RNN", raw.rnn],
    ["Accuracy", modelEvidence.evidence?.model_accuracy != null ? Number(modelEvidence.evidence.model_accuracy) * 100 : null],
    ["AUC", modelEvidence.evidence?.model_auc != null ? Number(modelEvidence.evidence.model_auc) * 100 : null],
  ];
  return entries
    .map(([name, score])=>[name, Number(score)])
    .filter(([,score])=>Number.isFinite(score))
    .slice(0,7);
}

export default function ModelScoresPanel({ modelEvidence }) {
  const models = collectScores(modelEvidence);
  return (
    <DashboardCard title="Model Scores" style={{height:150}}>
      {models.length===0 ? (
        <div style={{color:THEME.textMuted,fontSize:11,textAlign:"center",paddingTop:34,border:`1px dashed ${THEME.border}`,borderRadius:6,height:86,boxSizing:"border-box"}}>
          Backend model evidence unavailable.
        </div>
      ) : (
        <div style={{display:"grid",gridTemplateColumns:`repeat(${Math.min(models.length,7)},1fr)`,gap:8}}>
          {models.map(([name,s])=>{
            const c=s>=56?THEME.purple:s>=45?THEME.amber:THEME.red;
            return <div key={name} style={{textAlign:"center"}}>
              <div style={{fontSize:10,color:THEME.textMuted,marginBottom:5}}>{name}</div>
              <div style={{width:44,height:44,borderRadius:"50%",margin:"0 auto",display:"grid",placeItems:"center",background:`conic-gradient(${c} ${Math.max(0,Math.min(100,s))*3.6}deg, rgba(255,255,255,0.08) 0deg)`,boxShadow:`0 0 12px ${c}33`}}>
                <div style={{width:34,height:34,borderRadius:"50%",background:THEME.panel,display:"grid",placeItems:"center",fontSize:14,fontWeight:900,color:THEME.text}}>{s.toFixed(0)}</div>
              </div>
              <div style={{fontSize:10,color:s>=70?THEME.purple:s>=45?THEME.textDim:THEME.red,marginTop:4}}>{s>=70?"High":s>=55?"Moderate":s>=45?"Neutral":"High Risk"}</div>
            </div>;
          })}
          <div style={{gridColumn:"1/-1",fontSize:9,color:THEME.textMuted,marginTop:2}}>Scores are backend evidence values normalized 0-100.</div>
        </div>
      )}
    </DashboardCard>
  );
}
