import React from "react";
import DashboardCard, { THEME } from "./DashboardCard";
export default function WatchlistPanel({ symbols=[], selected, onSelect }) {
  return (
    <DashboardCard title="Watchlist">
      {symbols.length===0&&<div style={{color:THEME.textMuted,fontSize:10,textAlign:"center",padding:8}}>No symbols</div>}
      <div style={{overflowY:"auto",maxHeight:140}}>
        {symbols.map(s=>{
          const isSelected = s.symbol===selected;
          const up = s.change>=0;
          return (
            <div key={s.symbol} onClick={()=>onSelect?.(s.symbol)}
              style={{display:"flex",justifyContent:"space-between",alignItems:"center",
                padding:"5px 0",cursor:"pointer",borderBottom:`1px solid rgba(26,42,56,0.4)`,
                background:isSelected?"rgba(32,214,210,0.06)":"transparent"}}>
              <div>
                <div style={{fontSize:11,fontWeight:700,color:isSelected?THEME.cyan:THEME.text}}>{s.symbol}</div>
                <div style={{fontSize:9,color:THEME.textMuted}}>{s.name}</div>
              </div>
              <div style={{textAlign:"right"}}>
                <div style={{fontSize:11,fontWeight:700,color:THEME.text}}>{s.price||"—"}</div>
                {s.change!=null&&<div style={{fontSize:9,color:up?THEME.green:THEME.red}}>
                  {up?"▲":"▼"}{Math.abs(s.changePct||0).toFixed(2)}%
                </div>}
              </div>
            </div>
          );
        })}
      </div>
    </DashboardCard>
  );
}
