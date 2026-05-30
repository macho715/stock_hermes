import React from "react";
import { THEME } from "./DashboardCard";
export default function ActionPlanPanel({ result, safetyState=null }) {
  const fmt = (n,cur) => n!=null?(cur==="₩"?`₩${Math.round(n).toLocaleString("ko-KR")}`:`$${Number(n).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2})}`): "—";
  const cur = result?.ticker?.endsWith(".KS")||result?.ticker?.endsWith(".KQ") ? "₩" : "$";
  const val = (v) => v && Number(v) > 0 ? Number(v) : null;
  const entry = val(result?.entry ?? result?.latest_close);
  const stop = val(result?.stop);
  const tp1 = val(result?.tp1);
  const tp2 = val(result?.tp2);
  const zone = entry ? `${fmt(entry,cur)}${tp1 ? ` - ${fmt(tp1,cur)}` : ""}` : "—";
  const pctFromEntry = (target) => entry && target ? `${((target-entry)/entry*100)>=0?"+":""}${((target-entry)/entry*100).toFixed(1)}%` : "—";
  const rows = [
    ["ENTRY", entry, zone, THEME.purple],
    ["STOP LOSS", stop, pctFromEntry(stop), THEME.red],
    ["TAKE PROFIT 1 (TP1)", tp1, pctFromEntry(tp1), THEME.greenBright],
    ["TAKE PROFIT 2 (TP2)", tp2, pctFromEntry(tp2), THEME.greenBright],
  ];
  const blocked = safetyState?.actionPlanEnabled === false;
  if (blocked) {
    const blockers = Array.isArray(safetyState?.hardBlockers) ? safetyState.hardBlockers : [];
    return (
      <div>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",marginBottom:4}}>
          <div style={{fontSize:13,color:THEME.text,fontWeight:900,textTransform:"uppercase"}}>Action Plan <span style={{fontSize:10,color:THEME.textMuted}}>(Reference Only)</span></div>
          <div style={{fontSize:11,color:THEME.red,fontWeight:900}}>DISABLED BY RISK GATE</div>
        </div>
        <div style={{border:`1px solid ${THEME.red}77`,borderRadius:6,overflow:"hidden",background:"rgba(239,68,68,0.08)"}}>
          <div style={{padding:"8px 10px",borderBottom:`1px solid ${THEME.red}55`,fontSize:12,color:THEME.red,fontWeight:900}}>
            REFERENCE PLAN - DISABLED BY RISK GATE
          </div>
          <div style={{padding:"8px 10px",fontSize:11,color:THEME.textDim,lineHeight:1.5}}>
            Entry, stop loss, TP1, and TP2 are not actionable for this snapshot.
            <br/>
            Blocker: {blockers[0] || "LIVE_TRADING_NOT_ALLOWED"}
          </div>
        </div>
        <div style={{fontSize:9,color:THEME.textMuted,marginTop:5}}>
          This dashboard is report-only. No broker execution is enabled.
        </div>
      </div>
    );
  }
  return (
    <div>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",marginBottom:4}}>
        <div style={{fontSize:13,color:THEME.text,fontWeight:900,textTransform:"uppercase"}}>Action Plan <span style={{fontSize:10,color:THEME.textMuted}}>(Reference Only)</span></div>
        <div style={{fontSize:11,color:THEME.purple,fontWeight:900}}>REFERENCE ONLY</div>
      </div>
      <div style={{border:`1px solid ${THEME.border}`,borderRadius:6,overflow:"hidden"}}>
        {rows.map(([label,value,delta,color])=>(
          <div key={label} style={{display:"grid",gridTemplateColumns:"1.15fr 0.75fr 0.45fr",minHeight:22,alignItems:"center",borderBottom:`1px solid ${THEME.border}`}}>
            <span style={{fontSize:11,color:THEME.textDim,paddingLeft:10,fontWeight:800}}>{label}</span>
            <span style={{fontSize:11,color:THEME.text,fontWeight:800}}>{label==="ENTRY"?delta:fmt(value,cur)}</span>
            <span style={{fontSize:10,color,textAlign:"right",paddingRight:10}}>{label==="ENTRY"?"(Zone)":delta}</span>
          </div>
        ))}
      </div>
      <div style={{fontSize:9,color:THEME.textMuted,marginTop:5}}>
        This is a reference plan. Not financial advice. Do your own research.
      </div>
    </div>
  );
}
