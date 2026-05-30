import React from "react";
import { THEME } from "./DashboardCard";
export default function HeaderBar({ market, onMarketChange, ticker, onTickerChange, symbols=[], accent }) {
  const selected = symbols.find(s=>s.symbol===ticker);
  return (
    <header style={{height:62,display:"grid",gridTemplateColumns:"auto 1fr auto auto auto auto auto",alignItems:"center",gap:18,marginBottom:10,padding:"0 16px",
      background:"linear-gradient(180deg,rgba(5,10,15,0.98),rgba(3,7,10,0.98))",border:`1px solid ${THEME.border}`,borderRadius:10,boxShadow:"0 4px 18px rgba(0,0,0,0.22)"}}>
      <div style={{display:"flex",alignItems:"center",gap:12}}>
        <div style={{width:34,height:34,borderRadius:10,background:"linear-gradient(135deg,#8e4dff,#7132f5)",display:"grid",placeItems:"center",boxShadow:"0 0 18px rgba(113,50,245,0.38)"}}>
          <span style={{fontSize:24,fontWeight:900,color:"#0a1017",lineHeight:1}}>m</span>
        </div>
        <span style={{fontSize:26,fontWeight:900,color:THEME.text,letterSpacing:0}}>STOCK<span style={{color:THEME.purple}}>PRED</span></span>
        <span style={{fontSize:13,color:THEME.textDim,fontWeight:700}}>Executive Dashboard v2.1</span>
      </div>
      <div/>
      <div style={{display:"flex",alignItems:"center",gap:8}}>
        <span style={{fontSize:11,color:THEME.textMuted,fontWeight:800}}>Ticker</span>
      {symbols.length>0&&(
        <select aria-label="Select ticker" value={ticker||""} onChange={e=>onTickerChange?.(e.target.value)}
            style={{background:"rgba(7,13,18,0.98)",border:`1px solid ${THEME.borderHi}`,color:THEME.text,borderRadius:6,padding:"9px 34px 9px 12px",fontSize:16,fontWeight:800,minWidth:132}}>
          {symbols.map(s=><option key={s.symbol} value={s.symbol}>{s.symbol}</option>)}
        </select>
      )}
      </div>
      <div style={{minWidth:110}}>
        <div style={{fontSize:13,color:THEME.text,fontWeight:800}}>{selected?.name || "Apple Inc."}</div>
        <div style={{fontSize:11,color:THEME.textMuted,letterSpacing:"0.04em"}}>{market==="KRX"?"KOSPI/KOSDAQ":"NASDAQ"}</div>
      </div>
      <div style={{display:"flex",gap:6}}>
        {["US","KRX"].map(m=>(
          <button key={m} onClick={()=>onMarketChange?.(m)} aria-label={`Select market ${m}`}
            style={{minWidth:72,padding:"8px 16px",borderRadius:6,border:`1px solid ${market===m?THEME.purple:THEME.border}`,
              background:market===m?"linear-gradient(180deg,#8e4dff,#7132f5)":"rgba(255,255,255,0.02)",color:market===m?"#fff":THEME.textDim,
              cursor:"pointer",fontSize:12,fontWeight:800,boxShadow:market===m?"0 0 0 1px rgba(113,50,245,0.35), 0 0 16px rgba(113,50,245,0.22)":"none"}}>
            {m}
          </button>
        ))}
      </div>
      <div style={{fontSize:12,color:THEME.purple,fontWeight:900,letterSpacing:"0.08em",border:`1px solid ${THEME.purple}`,borderRadius:6,padding:"8px 16px",boxShadow:"0 0 14px rgba(113,50,245,0.24)"}} aria-live="polite">▣ REPORT ONLY</div>
      <div style={{fontSize:11,color:THEME.textMuted,lineHeight:1.25}}>
        <div>Last Update</div>
        <div>{new Date().toISOString().slice(0,19).replace("T"," ")}</div>
      </div>
    </header>
  );
}
