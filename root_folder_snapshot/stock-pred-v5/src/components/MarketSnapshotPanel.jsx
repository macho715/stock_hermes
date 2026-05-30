import React from "react";
import DashboardCard, { THEME } from "./DashboardCard";
function Row({label,value,color}){
  return <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",padding:"6px 0",borderBottom:`1px solid rgba(26,42,56,0.5)`}}>
    <span style={{fontSize:10,color:THEME.textMuted,textTransform:"uppercase",letterSpacing:"0.05em"}}>{label}</span>
    <span style={{fontSize:12,fontWeight:700,color:color||THEME.text}}>{value||"—"}</span>
  </div>;
}
export default function MarketSnapshotPanel({ result }) {
  const regime = result?.advisor_regime || "neutral";
  const rc = regime==="risk_on"?THEME.green:regime==="risk_off"?THEME.red:THEME.amber;
  const volRatio = result?.volume_ratio_20d;
  const volColor = volRatio==null?THEME.textDim:volRatio>=1.5?THEME.green:volRatio<0.8?THEME.red:THEME.textDim;
  return (
    <DashboardCard title="Market Snapshot">
      <Row label="Regime" value={regime.replace("_"," ").toUpperCase()} color={rc}/>
      <Row label="Model Score" value={result?.score!=null?`${Number(result.score).toFixed(1)}`:null} color={result?.score>=56?THEME.green:result?.score>=45?THEME.amber:THEME.red}/>
      <Row label="Probability" value={result?.probability!=null?`${(result.probability*100).toFixed(1)}%`:null}/>
      <Row label="Vol Ratio 20d" value={volRatio!=null?`${Number(volRatio).toFixed(2)}×`:null} color={volColor}/>
      <Row label="OOF Coverage" value={result?.oof_coverage!=null?`${(result.oof_coverage*100).toFixed(0)}%`:null}/>
      <Row label="Expected Val" value={result?.expected_value_pct!=null?`${Number(result.expected_value_pct).toFixed(2)}%`:null}/>
    </DashboardCard>
  );
}
