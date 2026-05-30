import React from "react";
import { THEME } from "./DashboardCard";
export default function ActionPlanPanel({ result }) {
  const fmt = (n,cur) => n!=null?(cur==="₩"?`₩${Math.round(n).toLocaleString("ko-KR")}`:`$${Number(n).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2})}`): "—";
  const cur = result?.ticker?.endsWith(".KS")||result?.ticker?.endsWith(".KQ") ? "₩" : "$";
  return (
    <div>
      <div style={{fontSize:9,color:THEME.textMuted,textTransform:"uppercase",letterSpacing:"0.06em",marginBottom:4}}>Action Plan</div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:4}}>
        {[["ENTRY",result?.entry,THEME.green],["STOP",result?.stop,THEME.red],["TP1",result?.tp1,THEME.green],["TP2",result?.tp2,THEME.green]].map(([l,v,c])=>(
          <div key={l} style={{textAlign:"center",background:"rgba(255,255,255,0.03)",borderRadius:4,padding:"4px 6px"}}>
            <div style={{fontSize:8,color:THEME.textMuted,letterSpacing:"0.05em"}}>{l}</div>
            <div style={{fontSize:10,fontWeight:700,color:c}}>{fmt(v,cur)}</div>
          </div>
        ))}
      </div>
      <div style={{fontSize:8,color:THEME.textMuted,marginTop:4,textAlign:"center"}}>
        Reference only · Manual review required
      </div>
    </div>
  );
}
