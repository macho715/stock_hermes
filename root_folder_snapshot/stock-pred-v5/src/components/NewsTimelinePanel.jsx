import React from "react";
import DashboardCard, { THEME } from "./DashboardCard";
export default function NewsTimelinePanel({ headlines=[] }) {
  return (
    <DashboardCard title="News Timeline">
      {headlines.length===0&&<div style={{color:THEME.textMuted,fontSize:10,textAlign:"center",padding:8}}>No news data · Enable NotebookLM for live news</div>}
      <div style={{overflowY:"auto",maxHeight:140}}>
        {headlines.slice(0,8).map((h,i)=>(
          <div key={i} style={{padding:"5px 0",borderBottom:`1px solid rgba(26,42,56,0.4)`}}>
            <div style={{fontSize:10,color:THEME.text,lineHeight:1.35,WebkitLineClamp:2,overflow:"hidden",display:"-webkit-box",WebkitBoxOrient:"vertical"}}>{h.title}</div>
            <div style={{fontSize:9,color:THEME.textMuted,marginTop:2}}>{h.source} {h.published_at?.slice(0,10)||""}</div>
          </div>
        ))}
      </div>
    </DashboardCard>
  );
}
