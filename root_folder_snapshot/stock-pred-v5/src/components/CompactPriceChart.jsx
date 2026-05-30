import React, { useMemo } from "react";
import { ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import DashboardCard, { THEME } from "./DashboardCard";
export default function CompactPriceChart({ ohlcvRecords=[], currency="$" }) {
  const data = useMemo(()=>ohlcvRecords.slice(-60).map(r=>({date:r.date?.slice(5)||"",close:r.close,volume:r.volume})),[ohlcvRecords]);
  if(!data.length) return <DashboardCard title="Price Chart"><div style={{height:200,display:"flex",alignItems:"center",justifyContent:"center",color:THEME.textMuted,fontSize:11}}>No chart data</div></DashboardCard>;
  const fmt = v=>currency==="$"?`$${Number(v).toFixed(0)}`:`₩${Math.round(v).toLocaleString()}`;
  return (
    <DashboardCard title="Price Chart (1D)" right={<div style={{display:"flex",gap:4}}>{["1D","5D","1M","3M","YTD","1Y"].map((t,i)=><span key={t} style={{fontSize:10,color:i===0?"#fff":THEME.textMuted,background:i===0?THEME.purple:"rgba(255,255,255,0.03)",border:`1px solid ${THEME.border}`,borderRadius:4,padding:"3px 8px"}}>{t}</span>)}</div>} style={{height:"100%"}}>
      <div style={{height:226,border:`1px solid ${THEME.border}`,background:"linear-gradient(180deg,rgba(113,50,245,0.06),rgba(0,0,0,0.08))"}}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{top:4,right:4,bottom:0,left:0}}>
            <XAxis dataKey="date" tick={{fill:THEME.textDim,fontSize:10}} stroke={THEME.border} interval="preserveStartEnd" minTickGap={30}/>
            <YAxis yAxisId="price" tick={{fill:THEME.textMuted,fontSize:9}} stroke={THEME.border} width={52} tickFormatter={fmt} domain={["auto","auto"]}/>
            <YAxis yAxisId="volume" hide domain={[0, "dataMax"]}/>
            <Tooltip contentStyle={{background:THEME.panel2,border:`1px solid ${THEME.border}`,borderRadius:6,fontSize:11,color:THEME.text}} labelStyle={{color:THEME.textDim}} formatter={(v)=>[fmt(v),"Close"]}/>
            <Bar yAxisId="volume" dataKey="volume" fill={THEME.green} opacity={0.45}/>
            <Line yAxisId="price" type="monotone" dataKey="close" stroke={THEME.purple} strokeWidth={2} dot={false}/>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </DashboardCard>
  );
}
