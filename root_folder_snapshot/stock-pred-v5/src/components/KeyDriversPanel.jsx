import React from "react";
import { THEME } from "./DashboardCard";
export default function KeyDriversPanel({ result }) {
  const drivers = [
    result?.validations?.filter(v=>v.status==="PASS").slice(0,3).map(v=>({label:v.name,positive:true}))||[],
    result?.validations?.filter(v=>v.status==="FAIL").slice(0,2).map(v=>({label:v.name,positive:false}))||[],
  ].flat();
  if(!drivers.length) return <div style={{color:THEME.textMuted,fontSize:10}}>No driver data</div>;
  return (
    <div>
      <div style={{fontSize:9,color:THEME.textMuted,textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:6}}>Key Drivers</div>
      {drivers.map((d,i)=><div key={i} style={{display:"flex",alignItems:"center",gap:5,marginBottom:3}}>
        <span style={{fontSize:9,color:d.positive?THEME.green:THEME.red}}>{d.positive?"▲":"▼"}</span>
        <span style={{fontSize:9,color:THEME.textDim}}>{d.label?.replace(/_/g," ")}</span>
      </div>)}
    </div>
  );
}
