import React from "react";
export const THEME = {
  bg:"#020916",panel:"rgba(9,20,36,0.94)",panel2:"rgba(12,28,48,0.92)",
  panelHi:"rgba(18,42,70,0.92)",border:"#1a2a38",borderHi:"#284057",
  text:"#d4e1ec",textDim:"#8a9bad",textMuted:"#536476",
  cyan:"#20d6d2",green:"#00ff88",red:"#ff4d57",amber:"#ffb020",
  blue:"#2f8cff",purple:"#a86bff",
};
export default function DashboardCard({ title, subtitle, right, children, style={} }) {
  return (
    <section style={{
      background:"linear-gradient(180deg,rgba(12,28,48,0.94),rgba(6,15,28,0.94))",
      border:`1px solid ${THEME.border}`,borderRadius:8,
      boxShadow:"0 8px 28px rgba(0,0,0,0.28)",overflow:"hidden",...style
    }}>
      {(title||right)&&(
        <header style={{height:40,padding:"0 14px",display:"flex",alignItems:"center",
          justifyContent:"space-between",borderBottom:`1px solid rgba(40,64,87,0.55)`}}>
          <div style={{display:"flex",alignItems:"baseline",gap:8}}>
            {title&&<span style={{fontSize:11,fontWeight:800,letterSpacing:"0.06em",
              textTransform:"uppercase",color:THEME.text}}>{title}</span>}
            {subtitle&&<span style={{fontSize:10,color:THEME.textMuted}}>{subtitle}</span>}
          </div>
          {right&&<div>{right}</div>}
        </header>
      )}
      <div style={{padding:"12px 14px"}}>{children}</div>
    </section>
  );
}
