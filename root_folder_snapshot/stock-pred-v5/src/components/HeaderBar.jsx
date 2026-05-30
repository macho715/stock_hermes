import React from "react";
import { THEME } from "./DashboardCard";
export default function HeaderBar({ market, onMarketChange, ticker, onTickerChange, symbols=[], accent }) {
  return (
    <header style={{height:52,display:"grid",gridTemplateColumns:"auto 1fr auto auto auto auto",alignItems:"center",gap:14,marginBottom:14}}>
      <div style={{display:"flex",alignItems:"center",gap:10}}>
        <span style={{fontSize:16,fontWeight:800,color:THEME.cyan,letterSpacing:"0.05em"}}>STOCK·PRED</span>
        <span style={{fontSize:10,color:THEME.textMuted,letterSpacing:"0.1em"}}>v2.1</span>
      </div>
      <div/>
      {symbols.length>0&&(
        <select aria-label="Select ticker" value={ticker||""} onChange={e=>onTickerChange?.(e.target.value)}
          style={{background:THEME.panel2,border:`1px solid ${THEME.border}`,color:THEME.text,borderRadius:4,padding:"4px 8px",fontSize:11}}>
          {symbols.map(s=><option key={s.symbol} value={s.symbol}>{s.symbol} — {s.name}</option>)}
        </select>
      )}
      <div style={{display:"flex",gap:6}}>
        {["US","KRX"].map(m=>(
          <button key={m} onClick={()=>onMarketChange?.(m)} aria-label={`Select market ${m}`}
            style={{padding:"4px 12px",borderRadius:4,border:`1px solid ${market===m?accent:THEME.border}`,
              background:market===m?`${accent}15`:"transparent",color:market===m?accent:THEME.textDim,
              cursor:"pointer",fontSize:11,fontWeight:700}}>
            {m}
          </button>
        ))}
      </div>
      <div style={{fontSize:10,color:THEME.textDim,letterSpacing:"0.06em"}} aria-live="polite">REPORT ONLY</div>
    </header>
  );
}
