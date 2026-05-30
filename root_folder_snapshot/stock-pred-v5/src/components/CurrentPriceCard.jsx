import React from "react";
import { THEME, panelStyle, labelStyle } from "./DashboardCard";
export default function CurrentPriceCard({ price, change, changePct, volume, currency="$", ohlcvRecords=[], asOf }) {
  const up = change >= 0;
  const chColor = up ? THEME.greenBright : THEME.red;
  const fmt = (n) => n!=null ? (currency==="$"?`$${Number(n).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2})}`:`₩${Math.round(n).toLocaleString("ko-KR")}`): "—";
  const closes = Array.isArray(ohlcvRecords) ? ohlcvRecords.slice(-24).map((d)=>Number(d.close)).filter(Number.isFinite) : [];
  const min = closes.length ? Math.min(...closes) : 0;
  const max = closes.length ? Math.max(...closes) : 0;
  const span = max > min ? max - min : 1;
  const points = closes.map((v,i)=>{
    const x = closes.length > 1 ? (i/(closes.length-1))*180 : 0;
    const y = 50 - ((v-min)/span)*40;
    return `${x.toFixed(1)} ${y.toFixed(1)}`;
  });
  const linePath = points.length ? `M${points.join(" L")}` : "";
  const areaPath = points.length ? `${linePath} L180 58 L0 58 Z` : "";
  return (
    <section style={{...panelStyle,padding:"16px 20px",height:118,boxSizing:"border-box",position:"relative",overflow:"hidden"}}>
      <div style={labelStyle}>Current Price</div>
      <div style={{fontSize:34,fontWeight:900,color:THEME.text,letterSpacing:"-0.02em",marginTop:6}}>{fmt(price)}</div>
      {change!=null&&<div style={{fontSize:12,color:chColor,marginTop:4,fontWeight:700}}>
        {up?"+":"-"}{fmt(Math.abs(change)).replace(currency,"")} ({(changePct>=0?"+":"")+Number(changePct||0).toFixed(2)}%)
      </div>}
      <svg viewBox="0 0 180 58" style={{position:"absolute",right:22,top:36,width:178,height:58,opacity:0.95}}>
        <defs>
          <linearGradient id="priceSpark" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={THEME.purple} stopOpacity="0.34"/>
            <stop offset="100%" stopColor={THEME.purple} stopOpacity="0"/>
          </linearGradient>
        </defs>
        {linePath&&<path d={linePath} fill="none" stroke={THEME.purple} strokeWidth="2"/>}
        {areaPath&&<path d={areaPath} fill="url(#priceSpark)"/>}
      </svg>
      {asOf&&<div style={{position:"absolute",right:24,bottom:14,fontSize:10,color:THEME.textMuted}}>{asOf}</div>}
    </section>
  );
}
