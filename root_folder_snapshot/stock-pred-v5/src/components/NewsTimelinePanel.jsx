import React from "react";
import DashboardCard, { THEME } from "./DashboardCard";
function displayText(value) {
  return String(value || "").replace(/\u2014/g, "-");
}
export default function NewsTimelinePanel({ headlines=[] }) {
  const rows = Array.isArray(headlines) ? headlines : [];
  return (
    <DashboardCard title="News Timeline" right={<span style={{fontSize:11,color:THEME.textMuted}}>View All</span>} style={{height:"100%"}}>
      <div style={{overflowY:"auto",maxHeight:150}}>
        {rows.length===0&&(
          <div style={{fontSize:11,color:THEME.textMuted,padding:"38px 0",textAlign:"center",border:`1px dashed ${THEME.border}`,borderRadius:6}}>
            No news timeline data returned by the current snapshot.
          </div>
        )}
        {rows.slice(0,8).map((h,i)=>(
          <div key={i} style={{display:"grid",gridTemplateColumns:"58px 1fr 96px",alignItems:"center",minHeight:30,borderBottom:`1px solid ${THEME.border}`}}>
            <span style={{fontSize:11,color:THEME.textMuted}}><span style={{width:8,height:8,borderRadius:"50%",background:h.color||THEME.green,display:"inline-block",marginRight:8}}/>{h.published_at?.slice(0,10)||h.published_at||""}</span>
            <div style={{fontSize:12,color:THEME.textDim,lineHeight:1.35,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{displayText(h.title)}</div>
            <div style={{fontSize:10,color:THEME.textMuted,textAlign:"right"}}>{h.source}</div>
          </div>
        ))}
        {rows.length>0&&<div style={{fontSize:11,color:THEME.purple,textAlign:"right",marginTop:8}}>More news →</div>}
      </div>
    </DashboardCard>
  );
}
