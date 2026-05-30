import React from "react";
export const THEME = {
  bg:"#05090d",bg2:"#081016",panel:"rgba(10,18,24,0.96)",panel2:"rgba(12,22,30,0.94)",
  panelHi:"rgba(17,29,39,0.96)",border:"rgba(104,107,130,0.28)",borderHi:"rgba(148,151,169,0.36)",
  text:"#f4f7fb",textDim:"#b6bfca",textMuted:"#7e8896",
  purple:"#7132f5",purpleDark:"#5741d8",purpleDeep:"#5b1ecf",purpleSoft:"rgba(133,91,251,0.18)",
  cyan:"#20d6d2",green:"#149e61",greenBright:"#27d27d",red:"#ef4444",amber:"#ffb020",
  blue:"#7b8cff",shadow:"0 8px 22px rgba(0,0,0,0.26), inset 0 1px 0 rgba(255,255,255,0.025)",
};
export const panelStyle = {
  background:"linear-gradient(180deg,rgba(13,23,31,0.98),rgba(6,13,18,0.98))",
  border:`1px solid ${THEME.border}`,
  borderRadius:10,
  boxShadow:THEME.shadow,
};
export const labelStyle = {
  fontSize:12,
  fontWeight:800,
  letterSpacing:"0.06em",
  textTransform:"uppercase",
  color:THEME.textMuted,
};
export default function DashboardCard({ title, subtitle, right, children, style={} }) {
  return (
    <section style={{
      ...panelStyle,overflow:"hidden",...style
    }}>
      {(title||right)&&(
        <header style={{height:36,padding:"0 14px",display:"flex",alignItems:"center",
          justifyContent:"space-between",borderBottom:`1px solid ${THEME.border}`}}>
          <div style={{display:"flex",alignItems:"baseline",gap:8}}>
            {title&&<span style={labelStyle}>{title}</span>}
            {subtitle&&<span style={{fontSize:10,color:THEME.textMuted}}>{subtitle}</span>}
          </div>
          {right&&<div>{right}</div>}
        </header>
      )}
      <div style={{padding:"10px 14px"}}>{children}</div>
    </section>
  );
}
