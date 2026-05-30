import React, { useMemo } from "react";
import { ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import DashboardCard, { THEME } from "./DashboardCard";
export default function CompactPriceChart({ ohlcvRecords=[], currency="$" }) {
  const data = useMemo(()=>ohlcvRecords.slice(-60).map(r=>({date:r.date?.slice(5)||"",close:r.close,volume:r.volume})),[ohlcvRecords]);
  if(!data.length) return <DashboardCard title="Price Chart"><div style={{height:200,display:"flex",alignItems:"center",justifyContent:"center",color:THEME.textMuted,fontSize:11}}>No chart data</div></DashboardCard>;
  const fmt = v=>currency==="$"?`$${Number(v).toFixed(0)}`:`₩${Math.round(v).toLocaleString()}`;
  return (
    <DashboardCard title="Price Chart" style={{minHeight:286,maxHeight:300}}>
      <div style={{height:220}}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{top:4,right:4,bottom:0,left:0}}>
            <XAxis dataKey="date" tick={{fill:THEME.textMuted,fontSize:9}} stroke={THEME.border} interval="preserveStartEnd" minTickGap={30}/>
            <YAxis tick={{fill:THEME.textMuted,fontSize:9}} stroke={THEME.border} width={52} tickFormatter={fmt} domain={["auto","auto"]}/>
            <Tooltip contentStyle={{background:THEME.panel2,border:`1px solid ${THEME.border}`,borderRadius:4,fontSize:11}} labelStyle={{color:THEME.textDim}} formatter={(v)=>[fmt(v),"Close"]}/>
            <Bar dataKey="volume" fill={THEME.border} opacity={0.5} yAxisId={0}/>
            <Line type="monotone" dataKey="close" stroke={THEME.cyan} strokeWidth={1.5} dot={false}/>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </DashboardCard>
  );
}
