import React from "react";
import { THEME } from "./DashboardCard";
export default function CurrentPriceCard({ price, change, changePct, volume, currency="$" }) {
  const up = change >= 0;
  const chColor = up ? THEME.green : THEME.red;
  const fmt = (n) => n!=null ? (currency==="$"?`$${Number(n).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2})}`:`₩${Math.round(n).toLocaleString("ko-KR")}`): "—";
  return (
    <section style={{background:"linear-gradient(180deg,rgba(12,28,48,0.94),rgba(6,15,28,0.94))",border:`1px solid ${THEME.border}`,borderRadius:8,padding:"14px 16px",boxShadow:"0 4px 16px rgba(0,0,0,0.24)"}}>
      <div style={{fontSize:10,color:THEME.textMuted,letterSpacing:"0.07em",textTransform:"uppercase",marginBottom:6}}>Current Price</div>
      <div style={{fontSize:26,fontWeight:800,color:THEME.text}}>{fmt(price)}</div>
      {change!=null&&<div style={{fontSize:12,color:chColor,marginTop:4,fontWeight:700}}>
        {up?"▲":"▼"} {fmt(Math.abs(change))} ({(changePct>=0?"+":"")+Number(changePct||0).toFixed(2)}%)
      </div>}
      {volume!=null&&<div style={{fontSize:10,color:THEME.textMuted,marginTop:4}}>Vol {(volume/1e6).toFixed(2)}M</div>}
    </section>
  );
}
