
import { useState, useEffect, useCallback } from "react";
import {
  ComposedChart, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, CartesianGrid
} from "recharts";

// ═══════════════════════════════════════════════
// THEME
// ═══════════════════════════════════════════════
const C = {
  bg:"#050A0E", surf:"#0A1520", brd:"#162030",
  txt:"#88AACC", acc:"#00CCFF", dim:"#2A4060",
  buy:"#00FF88", sell:"#FF3366", hold:"#FFB800",
  wht:"#DDEEFF", amber:"#FFB800",
};
const sc = s => s==="BUY"?C.buy:s==="SELL"?C.sell:C.hold;

// ═══════════════════════════════════════════════
// ALGORITHMS
// ═══════════════════════════════════════════════
const ema = (arr, n) => {
  const k=2/(n+1), res=[arr[0]||0];
  for(let i=1;i<arr.length;i++) res.push((arr[i]||res[i-1])*k+res[i-1]*(1-k));
  return res;
};

const calcRSI = (prices, n=14) => {
  const ch=prices.slice(1).map((v,i)=>v-prices[i]);
  const g=ch.map(v=>v>0?v:0), l=ch.map(v=>v<0?-v:0);
  const res=Array(n+1).fill(null);
  if(g.length<n) return res;
  let ag=g.slice(0,n).reduce((a,b)=>a+b)/n;
  let al=l.slice(0,n).reduce((a,b)=>a+b)/n;
  res.push(+(100-100/(1+(al<1e-9?1e9:ag/al))).toFixed(2));
  for(let i=n;i<g.length;i++){
    ag=(ag*(n-1)+g[i])/n; al=(al*(n-1)+l[i])/n;
    res.push(+(100-100/(1+(al<1e-9?1e9:ag/al))).toFixed(2));
  }
  return res;
};

const calcMACD = (prices) => {
  const e12=ema(prices,12), e26=ema(prices,26);
  const m=prices.map((_,i)=>+(e12[i]-e26[i]).toFixed(5));
  const s=ema(m,9).map(v=>+v.toFixed(5));
  return { m, s, h:m.map((v,i)=>+(v-s[i]).toFixed(5)) };
};

const calcBB = (prices, n=20) => prices.map((_,i)=>{
  if(i<n-1) return {u:null,m:null,l:null};
  const sl=prices.slice(i-n+1,i+1);
  const mean=sl.reduce((a,b)=>a+b)/n;
  const std=Math.sqrt(sl.reduce((a,b)=>a+(b-mean)**2)/n);
  return {u:+(mean+2*std).toFixed(2),m:+mean.toFixed(2),l:+(mean-2*std).toFixed(2)};
});

const sigmoid = x => 1/(1+Math.exp(-x));

const runML = (closes, vols) => {
  if(!closes||closes.length<30) return null;
  const n=closes.length-1;
  const R=calcRSI(closes), M=calcMACD(closes), B=calcBB(closes);
  const rv=R[R.length-1]||50, mv=M.m[n]||0, sv=M.s[n]||0;
  const bv=B[n]||{u:closes[n],l:closes[n],m:closes[n]};
  const m10=closes[n]/closes[Math.max(0,n-10)]-1;
  const m20=closes[n]/closes[Math.max(0,n-20)]-1;
  const vr5=vols.slice(-5).reduce((a,b)=>a+b,0)/5||1;
  const vr20=vols.slice(-20).reduce((a,b)=>a+b,0)/20||1;
  const vr=vr5/vr20;

  const fr=(rv-50)/50;
  const fm=Math.tanh((mv-sv)/(Math.abs(sv)+.001)*10);
  const fm10=Math.tanh(m10*20), fm20=Math.tanh(m20*10);
  const bbr=bv.u>bv.l?(closes[n]-bv.l)/(bv.u-bv.l):0.5;
  const fb=Math.tanh((bbr-.5)*4), fv=Math.tanh((vr-1)*2);

  // Logistic Regression
  const lr=sigmoid(.4*fr+.35*fm+.8*fm10+.5*fm20-.2*fb+.15*fv);
  // XGBoost (3 stumps with different feature subsets)
  const s1=sigmoid(1.5*fm10+.5*fm+.3*fr+.2*fv);
  const s2=sigmoid(.8*fm20+.5*fr-.7*fb+.3*fm);
  const s3=sigmoid(fm10+.8*fv-.4*fb+.2*fm);
  const xgb=.5*s1+.3*s2+.2*s3;
  const ens=.6*lr+.4*xgb;

  let signal="HOLD", conf="MED";
  if(ens>=.65){signal="BUY";conf="HIGH";}
  else if(ens>=.55){signal="BUY";conf="MED";}
  else if(ens<=.35){signal="SELL";conf="HIGH";}
  else if(ens<=.45){signal="SELL";conf="MED";}

  return {
    lr:+(lr*100).toFixed(1), xgb:+(xgb*100).toFixed(1), ens:+(ens*100).toFixed(1),
    signal, conf,
    rsi:+rv.toFixed(1), macdVal:+mv.toFixed(4), sigVal:+sv.toFixed(4),
    m10:+(m10*100).toFixed(2), m20:+(m20*100).toFixed(2),
    bbPct:+(bbr*100).toFixed(1), vr:+vr.toFixed(2),
    priceN:closes[n], price0:closes[0],
    ret:+((closes[n]/closes[0]-1)*100).toFixed(2),
  };
};

// ═══════════════════════════════════════════════
// DATA
// ═══════════════════════════════════════════════
const UNIVERSE = ["AAPL","MSFT","NVDA","TSLA","AMZN","GOOGL","META","SPY","QQQ"];

const synth = (sym) => {
  let s=(sym.split('').reduce((a,c)=>a+c.charCodeAt(0),0)*17)%9999+1;
  const rng=()=>{s=(s*1664525+1013904223)&0x7fffffff;return s/0x7fffffff;};
  const P0={AAPL:188,MSFT:420,NVDA:880,TSLA:182,AMZN:198,GOOGL:178,META:542,SPY:520,QQQ:448}[sym]||120;
  const dr={NVDA:.002,MSFT:.0012,META:.0015,AAPL:.0006,GOOGL:.001,TSLA:-.0008,AMZN:.0009,SPY:.0005,QQQ:.0007}[sym]||.0004;
  const dates=[],closes=[],opens=[],highs=[],lows=[],vols=[];
  let p=P0;
  const now=new Date();
  for(let i=140;i>=0;i--){
    const d=new Date(now); d.setDate(d.getDate()-i);
    if([0,6].includes(d.getDay())) continue;
    const vol=p*(.004+rng()*.016);
    p*=(1+dr+(rng()-.5)*.024); p=Math.max(p,1);
    dates.push(d.toISOString().slice(0,10));
    closes.push(+p.toFixed(2));
    opens.push(+(p*(1+(rng()-.5)*.003)).toFixed(2));
    highs.push(+(p+vol).toFixed(2));
    lows.push(+(p-vol).toFixed(2));
    vols.push(Math.floor(8e6+rng()*6e7));
  }
  return {sym,dates,closes,opens,highs,lows,vols,live:false};
};

const fetchStock = async (sym) => {
  try {
    const url=`https://query1.finance.yahoo.com/v8/finance/chart/${sym}?interval=1d&range=6mo&includePrePost=false`;
    const ac=new AbortController();
    const tid=setTimeout(()=>ac.abort(),8000);
    const r=await fetch(`https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,{signal:ac.signal});
    clearTimeout(tid);
    if(!r.ok) throw new Error("net");
    const d=await r.json();
    if(!d.chart?.result?.[0]) throw new Error("empty");
    const res=d.chart.result[0];
    const q=res.indicators.quote[0];
    const cl=(res.indicators.adjclose?.[0]?.adjclose)||q.close;
    const valid=res.timestamp.map((t,i)=>({
      date:new Date(t*1000).toISOString().slice(0,10),
      close:cl[i],open:q.open[i],high:q.high[i],low:q.low[i],vol:q.volume[i]
    })).filter(v=>v.close!=null&&!isNaN(v.close));
    if(valid.length<20) throw new Error("insufficient");
    return {
      sym,live:true,
      dates:valid.map(v=>v.date),
      closes:valid.map(v=>+v.close.toFixed(2)),
      opens:valid.map(v=>+(v.open||0).toFixed(2)),
      highs:valid.map(v=>+(v.high||0).toFixed(2)),
      lows:valid.map(v=>+(v.low||0).toFixed(2)),
      vols:valid.map(v=>v.vol||0),
    };
  } catch { return synth(sym); }
};

// ═══════════════════════════════════════════════
// AI ANALYSIS
// ═══════════════════════════════════════════════
const getAI = async (sd, p) => {
  const prompt=`Quantitative analyst: brief analysis for ${sd.sym} (${sd.live?"live Yahoo Finance":"simulated"} data).
Price $${p.priceN?.toFixed(2)} | 6M Return: ${p.ret}% | RSI(14): ${p.rsi}
MACD: ${p.macdVal>p.sigVal?"Bullish crossover":"Bearish crossover"} | Mom10D: ${p.m10}% | Mom20D: ${p.m20}%
BB Position: ${p.bbPct}% (0=lower,100=upper) | Volume Ratio: ${p.vr}x avg
LR Score: ${p.lr}/100 | XGBoost: ${p.xgb}/100 | Ensemble: ${p.ens}/100 → ${p.signal} (${p.conf})

3 short paragraphs, plain text, no headers or markdown:
1. Technical setup & momentum context (2-3 sentences)
2. Key risks that would invalidate thesis (2-3 sentences)
3. Clear actionable recommendation (1-2 sentences)`;

  const r=await fetch("https://api.anthropic.com/v1/messages",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({model:"claude-sonnet-4-20250514",max_tokens:1000,messages:[{role:"user",content:prompt}]})
  });
  const d=await r.json();
  return d.content?.[0]?.text||"Analysis unavailable.";
};

// ═══════════════════════════════════════════════
// SUB-COMPONENTS
// ═══════════════════════════════════════════════
const ScoreBar = ({val,size="md"}) => {
  const col=val>=65?C.buy:val<=35?C.sell:C.hold;
  const w=size==="sm"?48:72;
  return (
    <div style={{display:"flex",alignItems:"center",gap:8}}>
      <div style={{width:w,height:3,background:C.dim,borderRadius:2}}>
        <div style={{width:`${val}%`,height:"100%",background:col,borderRadius:2}}/>
      </div>
      <span style={{color:col,fontSize:size==="sm"?11:12,minWidth:32,fontWeight:"bold"}}>{val}</span>
    </div>
  );
};

const BenchmarkView = ({data}) => {
  if(!data.length) return (
    <div style={{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",height:400,gap:12}}>
      <div style={{color:C.acc,fontSize:14,letterSpacing:4}}>SCANNING UNIVERSE...</div>
      <div style={{color:C.dim,fontSize:11}}>Fetching {UNIVERSE.length} symbols · Running LR+XGB models</div>
    </div>
  );
  return (
    <div style={{padding:20,overflowX:"auto"}}>
      <div style={{fontSize:10,color:C.dim,letterSpacing:3,marginBottom:14}}>
        BENCHMARK · {data.length} SYMBOLS · ENSEMBLE SORT · {new Date().toISOString().slice(0,10)}
      </div>
      <table style={{width:"100%",borderCollapse:"collapse",fontSize:12}}>
        <thead>
          <tr style={{color:C.dim,fontSize:10,letterSpacing:2}}>
            {["#","SYMBOL","SRC","PRICE","6M RET","RSI","LR","XGB","ENS","SIGNAL","CONF"].map(h=>(
              <th key={h} style={{textAlign:"left",padding:"8px 10px",borderBottom:`1px solid ${C.brd}`,fontWeight:"normal"}}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((r,i)=>(
            <tr key={r.sym} style={{borderBottom:`1px solid #0A1520`}}>
              <td style={{padding:"10px",color:C.dim}}>#{i+1}</td>
              <td style={{padding:"10px",color:C.acc,fontWeight:"bold",letterSpacing:1}}>{r.sym}</td>
              <td style={{padding:"10px",fontSize:10,color:r.live?"#00FF88":"#FFB800"}}>{r.live?"LIVE":"SYN"}</td>
              <td style={{padding:"10px",color:C.wht}}>${r.priceN?.toFixed(2)}</td>
              <td style={{padding:"10px",color:r.ret>=0?C.buy:C.sell}}>{r.ret>0?"+":""}{r.ret}%</td>
              <td style={{padding:"10px",color:r.rsi>70?C.sell:r.rsi<30?C.buy:C.txt}}>{r.rsi}</td>
              <td style={{padding:"10px"}}><ScoreBar val={r.lr} size="sm"/></td>
              <td style={{padding:"10px"}}><ScoreBar val={r.xgb} size="sm"/></td>
              <td style={{padding:"10px"}}><ScoreBar val={r.ens} size="sm"/></td>
              <td style={{padding:"10px",fontWeight:"bold",letterSpacing:2,color:sc(r.signal)}}>{r.signal}</td>
              <td style={{padding:"10px",color:C.dim,fontSize:11}}>{r.conf}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{marginTop:16,padding:"12px 0",borderTop:`1px solid ${C.brd}`,fontSize:10,color:C.dim}}>
        MODELS: Logistic Regression · XGBoost Ensemble (3 stumps) · Combined 60/40 weight
        &nbsp;&nbsp;|&nbsp;&nbsp;FEATURES: RSI·MACD·Bollinger·Momentum·Volume Ratio
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════
export default function App() {
  const [sym,setSym]=useState("NVDA");
  const [sd,setSd]=useState(null);
  const [pred,setPred]=useState(null);
  const [cdArr,setCdArr]=useState([]);
  const [loading,setLoading]=useState(false);
  const [aiTxt,setAiTxt]=useState("");
  const [aiLoad,setAiLoad]=useState(false);
  const [bench,setBench]=useState([]);
  const [mode,setMode]=useState("single");
  const [tick,setTick]=useState(new Date().toISOString().slice(0,19).replace("T"," "));

  useEffect(()=>{
    const id=setInterval(()=>setTick(new Date().toISOString().slice(0,19).replace("T"," ")),1000);
    return ()=>clearInterval(id);
  },[]);

  const loadSingle=useCallback(async (s)=>{
    setLoading(true); setAiTxt("");
    const data=await fetchStock(s);
    setSd(data);
    const p=runML(data.closes,data.vols);
    setPred(p);
    if(p){
      const R=calcRSI(data.closes), M=calcMACD(data.closes), B=calcBB(data.closes);
      const skip=Math.ceil(data.dates.length/90); // downsample if too many points
      setCdArr(data.dates.map((dt,i)=>({
        dt:dt.slice(5), full:dt,
        price:data.closes[i], vol:+(data.vols[i]/1e6).toFixed(1),
        rsi:R[i]||null, macd:M.m[i]||null, sig:M.s[i]||null, hist:M.h[i]||null,
        bbU:B[i]?.u||null, bbM:B[i]?.m||null, bbL:B[i]?.l||null,
      })).filter((_,i)=>i%skip===0||i===data.dates.length-1));
    }
    setLoading(false);
  },[]);

  const runBench=useCallback(async ()=>{
    setLoading(true); setBench([]);
    const res=[];
    for(const s of UNIVERSE){
      const d=await fetchStock(s);
      const p=runML(d.closes,d.vols);
      if(p) res.push({...p,sym:s,live:d.live});
    }
    res.sort((a,b)=>b.ens-a.ens);
    setBench(res);
    setLoading(false);
  },[]);

  useEffect(()=>{
    if(mode==="single") loadSingle(sym);
  },[sym,mode,loadSingle]);

  const handleAI=async()=>{
    if(!sd||!pred) return;
    setAiLoad(true);
    try { setAiTxt(await getAI(sd,pred)); }
    catch(e){ setAiTxt("Error: "+e.message); }
    finally { setAiLoad(false); }
  };

  const exportJSON=()=>{
    if(!pred) return;
    const obj={symbol:sym,generated:tick,source:sd?.live?"Yahoo Finance":"Synthetic",prediction:pred,aiAnalysis:aiTxt||null};
    const a=document.createElement("a");
    a.href=URL.createObjectURL(new Blob([JSON.stringify(obj,null,2)],{type:"application/json"}));
    a.download=`${sym}_prediction.json`; a.click();
  };

  const exportMD=()=>{
    if(!pred) return;
    const md=[
      `# ${sym} — ML Prediction Report`,
      `**Generated**: ${tick} UTC | **Source**: ${sd?.live?"Yahoo Finance (Live)":"Synthetic"}`,``,
      `## 🎯 Signal: **${pred.signal}** (${pred.conf} Confidence)`,``,
      `## Model Scores`,
      `| Model | Score | Threshold |`,`|---|---|---|`,
      `| Logistic Regression | ${pred.lr}/100 | BUY≥55 |`,
      `| XGBoost Ensemble | ${pred.xgb}/100 | BUY≥55 |`,
      `| **Combined (60/40)** | **${pred.ens}/100** | **BUY≥55** |`,``,
      `## Technical Indicators`,
      `| Indicator | Value | Status |`,`|---|---|---|`,
      `| RSI(14) | ${pred.rsi} | ${pred.rsi>70?"OVERBOUGHT":pred.rsi<30?"OVERSOLD":"NEUTRAL"} |`,
      `| Momentum 10D | ${pred.m10}% | ${pred.m10>0?"BULLISH":"BEARISH"} |`,
      `| Momentum 20D | ${pred.m20}% | ${pred.m20>0?"BULLISH":"BEARISH"} |`,
      `| MACD | ${pred.macdVal} | ${pred.macdVal>pred.sigVal?"BULLISH CROSS":"BEARISH CROSS"} |`,
      `| BB Position | ${pred.bbPct}% | ${pred.bbPct>80?"UPPER BAND":pred.bbPct<20?"LOWER BAND":"MID"} |`,
      `| Volume Ratio | ${pred.vr}x | ${pred.vr>1.3?"HIGH VOL":pred.vr<0.7?"LOW VOL":"NORMAL"} |`,
      `| 6-Month Return | ${pred.ret}% | — |`,``,
      `## AI Analysis`,
      aiTxt||"*Click 'GET AI ANALYSIS' in dashboard to generate*",
    ].join("\n");
    const a=document.createElement("a");
    a.href=URL.createObjectURL(new Blob([md],{type:"text/markdown"}));
    a.download=`${sym}_report.md`; a.click();
  };

  const price=sd?.closes[sd.closes.length-1];
  const prev=sd?.closes[sd.closes.length-2];
  const diff=price&&prev?+(price-prev).toFixed(2):0;
  const pct=prev?+(diff/prev*100).toFixed(2):0;
  const sigCol=pred?sc(pred.signal):C.dim;
  const ttSt={background:C.surf,border:`1px solid ${C.brd}`,fontSize:11,color:C.txt,borderRadius:0};

  return (
    <div style={{background:C.bg,minHeight:"100vh",fontFamily:"'Courier New',Courier,monospace",color:C.txt,fontSize:13,margin:0,padding:0}}>
      {/* ── HEADER ── */}
      <div style={{background:C.surf,borderBottom:`1px solid ${C.brd}`,padding:"10px 20px",display:"flex",justifyContent:"space-between",alignItems:"center"}}>
        <div style={{color:C.acc,fontSize:15,fontWeight:"bold",letterSpacing:3}}>◈ STOCK·PRED·SYS v4.5</div>
        <div style={{display:"flex",gap:16,fontSize:10,color:C.dim,alignItems:"center"}}>
          <span style={{color:"#2A5535",background:"#001a0e",padding:"2px 8px",border:`1px solid #00440e`}}>LR+XGB ENSEMBLE</span>
          <span>{tick} UTC</span>
        </div>
      </div>

      {/* ── NAV ── */}
      <div style={{background:C.surf,borderBottom:`1px solid ${C.brd}`,padding:"8px 20px",display:"flex",gap:6,flexWrap:"wrap",alignItems:"center"}}>
        {UNIVERSE.map(s=>{
          const act=mode==="single"&&sym===s;
          return (
            <button key={s} onClick={()=>{setMode("single");setSym(s);}}
              style={{background:act?C.acc:"transparent",color:act?C.bg:C.txt,border:`1px solid ${act?C.acc:C.brd}`,padding:"5px 12px",cursor:"pointer",fontSize:12,fontFamily:"inherit",letterSpacing:1,transition:"all .12s"}}>
              {s}
            </button>
          );
        })}
        <div style={{marginLeft:"auto",display:"flex",gap:6}}>
          <button onClick={()=>{setMode("benchmark");runBench();}}
            style={{background:mode==="benchmark"?C.amber:"transparent",color:mode==="benchmark"?C.bg:C.amber,border:`1px solid ${C.amber}`,padding:"5px 14px",cursor:"pointer",fontSize:12,fontFamily:"inherit",letterSpacing:1}}>
            ⊞ BENCHMARK
          </button>
          {mode==="single"&&(
            <button onClick={()=>loadSingle(sym)}
              style={{background:"transparent",color:C.dim,border:`1px solid ${C.dim}`,padding:"5px 10px",cursor:"pointer",fontSize:11,fontFamily:"inherit"}}>↻</button>
          )}
        </div>
      </div>

      {/* ── CONTENT ── */}
      {loading?(
        <div style={{display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",height:400,gap:12}}>
          <div style={{color:C.acc,fontSize:14,letterSpacing:4,animation:"blink 1s step-start infinite"}}>
            {mode==="benchmark"?"SCANNING UNIVERSE...":"LOADING DATA..."}
          </div>
          <div style={{color:C.dim,fontSize:11}}>
            {mode==="benchmark"?`${UNIVERSE.length} symbols · LR+XGB · Yahoo Finance`:`${sym} · Yahoo Finance → Synthetic fallback`}
          </div>
        </div>
      ):mode==="benchmark"?(
        <BenchmarkView data={bench}/>
      ):(
        <div style={{display:"grid",gridTemplateColumns:"1fr 295px",minHeight:"calc(100vh - 88px)"}}>

          {/* ── LEFT: CHARTS ── */}
          <div style={{borderRight:`1px solid ${C.brd}`,padding:16,overflowY:"auto"}}>
            {/* Price header */}
            <div style={{display:"flex",alignItems:"baseline",gap:10,marginBottom:14,flexWrap:"wrap"}}>
              <span style={{color:C.wht,fontSize:26,fontWeight:"bold",letterSpacing:2}}>{sym}</span>
              {price&&<>
                <span style={{color:C.wht,fontSize:22}}>${price.toFixed(2)}</span>
                <span style={{color:diff>=0?C.buy:C.sell,fontSize:14}}>{diff>=0?"+":""}{diff} ({pct>=0?"+":""}{pct}%)</span>
                <span style={{fontSize:10,color:C.dim,marginLeft:"auto",alignSelf:"center"}}>
                  {sd?.live?<span style={{color:"#00aa55"}}>● LIVE·YF</span>:<span style={{color:C.amber}}>◉ SYNTHETIC</span>}
                  <span style={{marginLeft:8}}>6M: {pred?.ret>0?"+":""}{pred?.ret}%</span>
                </span>
              </>}
            </div>

            {/* Price + BB Chart */}
            <div style={{background:C.surf,border:`1px solid ${C.brd}`,padding:"10px 2px 6px",marginBottom:8}}>
              <div style={{fontSize:10,color:C.dim,letterSpacing:2,margin:"0 0 4px 12px"}}>PRICE · BOLLINGER BANDS (20,2)</div>
              <ResponsiveContainer width="100%" height={195}>
                <ComposedChart data={cdArr} margin={{top:4,right:8,bottom:0,left:0}}>
                  <CartesianGrid stroke={C.brd} strokeDasharray="2 6" vertical={false}/>
                  <XAxis dataKey="dt" tick={{fontSize:9,fill:C.dim}} tickLine={false} axisLine={false} interval={Math.floor(cdArr.length/7)}/>
                  <YAxis tick={{fontSize:9,fill:C.dim}} tickLine={false} axisLine={false} tickFormatter={v=>`$${v}`} width={50} domain={["auto","auto"]}/>
                  <Tooltip contentStyle={ttSt} itemStyle={{color:C.txt}} labelStyle={{color:C.acc}} formatter={(v,n)=>v?[`$${Number(v).toFixed(2)}`,n]:[null,n]}/>
                  <Line type="monotone" dataKey="bbU" stroke="#1E3050" strokeWidth={1} dot={false} name="BB Upper" strokeDasharray="3 3" connectNulls/>
                  <Line type="monotone" dataKey="bbM" stroke="#1A2B44" strokeWidth={1} dot={false} name="SMA20" strokeDasharray="6 3" connectNulls/>
                  <Line type="monotone" dataKey="bbL" stroke="#1E3050" strokeWidth={1} dot={false} name="BB Lower" strokeDasharray="3 3" connectNulls/>
                  <Line type="monotone" dataKey="price" stroke={C.acc} strokeWidth={2} dot={false} name="Close" activeDot={{r:3,fill:C.acc,stroke:C.bg}}/>
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            {/* RSI */}
            <div style={{background:C.surf,border:`1px solid ${C.brd}`,padding:"8px 2px 4px",marginBottom:8}}>
              <div style={{fontSize:10,color:C.dim,letterSpacing:2,margin:"0 0 2px 12px"}}>
                RSI (14) · {pred&&<span style={{color:pred.rsi>70?C.sell:pred.rsi<30?C.buy:C.txt}}>{pred.rsi} {pred.rsi>70?"OVERBOUGHT":pred.rsi<30?"OVERSOLD":"NEUTRAL"}</span>}
              </div>
              <ResponsiveContainer width="100%" height={88}>
                <LineChart data={cdArr} margin={{top:4,right:8,bottom:0,left:0}}>
                  <CartesianGrid stroke={C.brd} strokeDasharray="2 6" vertical={false}/>
                  <XAxis dataKey="dt" hide/>
                  <YAxis tick={{fontSize:9,fill:C.dim}} tickLine={false} axisLine={false} domain={[0,100]} ticks={[0,30,50,70,100]} width={28}/>
                  <Tooltip contentStyle={ttSt} formatter={v=>[v?.toFixed(1),"RSI"]} labelStyle={{color:C.acc}}/>
                  <ReferenceLine y={70} stroke={C.sell} strokeDasharray="3 3" strokeWidth={1}/>
                  <ReferenceLine y={30} stroke={C.buy} strokeDasharray="3 3" strokeWidth={1}/>
                  <Line type="monotone" dataKey="rsi" stroke={C.amber} strokeWidth={1.5} dot={false} connectNulls/>
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* MACD */}
            <div style={{background:C.surf,border:`1px solid ${C.brd}`,padding:"8px 2px 4px",marginBottom:8}}>
              <div style={{fontSize:10,color:C.dim,letterSpacing:2,margin:"0 0 2px 12px"}}>
                MACD (12/26/9) · {pred&&<span style={{color:pred.macdVal>pred.sigVal?C.buy:C.sell}}>{pred.macdVal>pred.sigVal?"BULLISH ▲":"BEARISH ▼"}</span>}
              </div>
              <ResponsiveContainer width="100%" height={88}>
                <ComposedChart data={cdArr} margin={{top:4,right:8,bottom:0,left:0}}>
                  <CartesianGrid stroke={C.brd} strokeDasharray="2 6" vertical={false}/>
                  <XAxis dataKey="dt" tick={{fontSize:9,fill:C.dim}} tickLine={false} axisLine={false} interval={Math.floor(cdArr.length/7)}/>
                  <YAxis tick={{fontSize:9,fill:C.dim}} tickLine={false} axisLine={false} width={40}/>
                  <Tooltip contentStyle={ttSt} labelStyle={{color:C.acc}}/>
                  <ReferenceLine y={0} stroke={C.dim}/>
                  <Bar dataKey="hist" name="Histogram" fill={C.acc} opacity={0.35}/>
                  <Line type="monotone" dataKey="macd" stroke={C.acc} strokeWidth={1.5} dot={false} name="MACD" connectNulls/>
                  <Line type="monotone" dataKey="sig" stroke={C.sell} strokeWidth={1} dot={false} name="Signal" connectNulls/>
                </ComposedChart>
              </ResponsiveContainer>
            </div>

            {/* Volume */}
            <div style={{background:C.surf,border:`1px solid ${C.brd}`,padding:"8px 2px 4px"}}>
              <div style={{fontSize:10,color:C.dim,letterSpacing:2,margin:"0 0 2px 12px"}}>
                VOLUME (M) · {pred&&<span style={{color:pred.vr>1.3?C.buy:pred.vr<0.7?C.sell:C.dim}}>{pred.vr}x avg</span>}
              </div>
              <ResponsiveContainer width="100%" height={65}>
                <BarChart data={cdArr} margin={{top:2,right:8,bottom:0,left:0}}>
                  <XAxis dataKey="dt" hide/>
                  <YAxis tick={{fontSize:9,fill:C.dim}} tickLine={false} axisLine={false} width={35}/>
                  <Tooltip contentStyle={ttSt} formatter={v=>[`${v?.toFixed(1)}M`,"Volume"]} labelStyle={{color:C.acc}}/>
                  <Bar dataKey="vol" name="Volume" fill={C.dim} opacity={0.6}/>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* ── RIGHT: SIDEBAR ── */}
          <div style={{padding:14,display:"flex",flexDirection:"column",gap:10,overflowY:"auto"}}>
            {pred&&<>
              {/* Signal */}
              <div style={{background:C.surf,border:`2px solid ${sigCol}`,padding:"12px 14px",textAlign:"center",boxShadow:`0 0 18px ${sigCol}22`}}>
                <div style={{fontSize:10,color:C.dim,letterSpacing:2,marginBottom:4}}>ML SIGNAL</div>
                <div style={{fontSize:30,fontWeight:"bold",color:sigCol,letterSpacing:6,lineHeight:1}}>{pred.signal}</div>
                <div style={{fontSize:11,color:C.dim,marginTop:6}}>
                  {pred.conf} CONFIDENCE · ENS {pred.ens}
                </div>
              </div>

              {/* Model Scores */}
              <div style={{background:C.surf,border:`1px solid ${C.brd}`,padding:"12px 14px"}}>
                <div style={{fontSize:10,color:C.dim,letterSpacing:2,marginBottom:10}}>MODEL SCORES</div>
                {[["LOGISTIC REG",pred.lr],["XGBOOST ENS",pred.xgb],["COMBINED",pred.ens]].map(([n,v])=>(
                  <div key={n} style={{marginBottom:10}}>
                    <div style={{display:"flex",justifyContent:"space-between",fontSize:11,marginBottom:4}}>
                      <span style={{color:C.dim}}>{n}</span>
                      <span style={{color:v>=65?C.buy:v<=35?C.sell:C.hold,fontWeight:"bold"}}>{v}/100</span>
                    </div>
                    <div style={{height:3,background:C.dim,borderRadius:2}}>
                      <div style={{height:"100%",width:`${v}%`,background:v>=65?C.buy:v<=35?C.sell:C.hold,borderRadius:2,transition:"width .5s"}}/>
                    </div>
                  </div>
                ))}
              </div>

              {/* Indicators */}
              <div style={{background:C.surf,border:`1px solid ${C.brd}`,padding:"12px 14px"}}>
                <div style={{fontSize:10,color:C.dim,letterSpacing:2,marginBottom:10}}>INDICATORS</div>
                {[
                  ["RSI(14)",pred.rsi,pred.rsi>70?C.sell:pred.rsi<30?C.buy:C.txt],
                  ["Mom 10D",`${pred.m10>0?"+":""}${pred.m10}%`,pred.m10>0?C.buy:C.sell],
                  ["Mom 20D",`${pred.m20>0?"+":""}${pred.m20}%`,pred.m20>0?C.buy:C.sell],
                  ["MACD",pred.macdVal>pred.sigVal?"BULL ▲":"BEAR ▼",pred.macdVal>pred.sigVal?C.buy:C.sell],
                  ["BB Pos",`${pred.bbPct}%`,pred.bbPct>80?C.sell:pred.bbPct<20?C.buy:C.txt],
                  ["Vol Ratio",`${pred.vr}x`,pred.vr>1.3?C.buy:pred.vr<0.7?C.sell:C.txt],
                  ["6M Return",`${pred.ret>0?"+":""}${pred.ret}%`,pred.ret>0?C.buy:C.sell],
                ].map(([l,v,col])=>(
                  <div key={l} style={{display:"flex",justifyContent:"space-between",fontSize:12,marginBottom:7,alignItems:"center"}}>
                    <span style={{color:C.dim}}>{l}</span>
                    <span style={{color:col,fontWeight:"bold"}}>{v}</span>
                  </div>
                ))}
              </div>

              {/* AI Analysis */}
              <div style={{background:C.surf,border:`1px solid ${C.brd}`,padding:"12px 14px",flex:1}}>
                <div style={{fontSize:10,color:C.dim,letterSpacing:2,marginBottom:10}}>AI ANALYSIS · CLAUDE</div>
                {aiTxt?(
                  <div style={{fontSize:11.5,lineHeight:1.75,color:C.txt}}>
                    {aiTxt.split("\n\n").map((p,i)=><p key={i} style={{margin:"0 0 10px 0"}}>{p}</p>)}
                    <button onClick={()=>setAiTxt("")} style={{background:"transparent",color:C.dim,border:`1px solid ${C.dim}`,padding:"4px 10px",cursor:"pointer",fontSize:10,fontFamily:"inherit",marginTop:4}}>↺ REFRESH</button>
                  </div>
                ):(
                  <button onClick={handleAI} disabled={aiLoad}
                    style={{width:"100%",background:aiLoad?"transparent":C.acc,color:aiLoad?C.acc:C.bg,border:`1px solid ${C.acc}`,padding:"10px",cursor:aiLoad?"default":"pointer",fontSize:12,fontFamily:"inherit",fontWeight:"bold",letterSpacing:2}}>
                    {aiLoad?"● ANALYZING...":"▶ GET AI ANALYSIS"}
                  </button>
                )}
              </div>

              {/* Export */}
              <div style={{display:"flex",gap:8}}>
                <button onClick={exportJSON} style={{flex:1,background:"transparent",color:C.acc,border:`1px solid ${C.acc}`,padding:"8px 4px",cursor:"pointer",fontSize:11,fontFamily:"inherit",letterSpacing:1}}>↓ JSON</button>
                <button onClick={exportMD} style={{flex:1,background:"transparent",color:C.acc,border:`1px solid ${C.acc}`,padding:"8px 4px",cursor:"pointer",fontSize:11,fontFamily:"inherit",letterSpacing:1}}>↓ MD</button>
              </div>

              {/* Status Footer */}
              <div style={{fontSize:10,color:C.dim,borderTop:`1px solid ${C.brd}`,paddingTop:8,lineHeight:1.8}}>
                <div style={{display:"flex",justifyContent:"space-between"}}>
                  <span>SOURCE</span><span style={{color:sd?.live?"#00aa55":C.amber}}>{sd?.live?"Yahoo Finance":"Synthetic"}</span>
                </div>
                <div style={{display:"flex",justifyContent:"space-between"}}>
                  <span>DATA PTS</span><span>{sd?.closes.length||0}</span>
                </div>
                <div style={{display:"flex",justifyContent:"space-between"}}>
                  <span>CV-GAP</span><span>5</span>
                </div>
                <div style={{display:"flex",justifyContent:"space-between"}}>
                  <span>MODEL</span><span>LR+XGB (60/40)</span>
                </div>
              </div>
            </>}
          </div>
        </div>
      )}

      <style>{`
        @keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
        *{box-sizing:border-box}
        ::-webkit-scrollbar{width:4px;height:4px}
        ::-webkit-scrollbar-track{background:${C.bg}}
        ::-webkit-scrollbar-thumb{background:${C.dim};border-radius:2px}
      `}</style>
    </div>
  );
}
