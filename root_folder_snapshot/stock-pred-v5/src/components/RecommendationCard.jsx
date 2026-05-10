import React from "react";
import RiskGateBadge from "./RiskGateBadge";
import KevpeBadge from "./KevpeBadge";

const C = {
  bg: "#050A0E",
  bgDeep: "#02060A",
  panel: "#0A1218",
  panel2: "#0E1822",
  panelHi: "#13202C",
  border: "#1A2A38",
  borderHi: "#243648",
  text: "#D4E1EC",
  textDim: "#6B7E8E",
  textMuted: "#3F5060",
  green: "#00FF88",
  red: "#FF3366",
  amber: "#FFB800",
  us: "#00CCFF",
  krx: "#FF6B35",
};

function fmtMoney(v, currency = "$") {
  if (v == null) return "—";
  return currency === "₩" ? `₩${Math.round(v).toLocaleString()}` : `$${Number(v).toFixed(2)}`;
}
function fmtPct(v) {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${Number(v).toFixed(2)}%`;
}
function fmtRatio(v) {
  if (v == null) return "—";
  return `${Number(v).toFixed(2)}×`;
}

export default function RecommendationCard({ result, currency = "$", accent = "#00CCFF", onClick }) {
  if (!result) return null;
  const isGreen = result.verdict?.includes("ELIGIBLE") || result.verdict?.includes("ACCUMULATE");
  const isAmber = result.verdict?.includes("AMBER");
  const isRed = result.verdict?.startsWith("RED") || result.verdict?.startsWith("ZERO");
  const borderColor = isGreen ? C.green : isAmber ? C.amber : isRed ? C.red : C.border;

  return (
    <div
      onClick={onClick}
      style={{
        background: C.panel,
        border: `1px solid ${borderColor}55`,
        borderLeft: `3px solid ${borderColor}`,
        padding: "10px 12px",
        marginBottom: 8,
        cursor: onClick ? "pointer" : "default",
        transition: "background .15s",
      }}
      onMouseEnter={(e) => { if (onClick) e.currentTarget.style.background = C.panel2; }}
      onMouseLeave={(e) => { e.currentTarget.style.background = C.panel; }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 14, fontWeight: 700, color: accent, letterSpacing: 2 }}>
            {result.ticker?.replace(".KS", "") || result.rank + "."}
          </span>
          <RiskGateBadge verdict={result.verdict} size={9} />
          <KevpeBadge result={result} size={8} />
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: borderColor }}>
            {result.score != null ? Math.round(result.score) : "—"}
          </div>
          <div style={{ fontSize: 8, color: C.textMuted, letterSpacing: 1 }}>SCORE</div>
        </div>
      </div>

      {/* Track + Probability */}
      <div style={{ display: "flex", gap: 12, marginBottom: 6, fontSize: 9, color: C.textDim }}>
        <span style={{ color: result.track === "S" ? C.us : C.krx, fontWeight: 600, letterSpacing: 1 }}>
          Track-{result.track || "—"}
        </span>
        {result.probability != null && (
          <span>Prob: <span style={{ color: C.text }}>{Number(result.probability).toFixed(2)}</span></span>
        )}
        {result.expected_value_pct != null && (
          <span>EV: <span style={{ color: Number(result.expected_value_pct) >= 0 ? C.green : C.red }}>{fmtPct(result.expected_value_pct)}</span></span>
        )}
      </div>

      {/* Entry / Stop / TP2 */}
      {result.entry != null && (
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 1fr 1fr",
          gap: 4, padding: "6px 8px",
          background: C.bgDeep, borderRadius: 3, marginBottom: 4,
        }}>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 7, color: C.textMuted, letterSpacing: 1 }}>ENTRY</div>
            <div style={{ fontSize: 11, color: C.text, fontWeight: 500 }}>{fmtMoney(result.entry, currency)}</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 7, color: C.textMuted, letterSpacing: 1 }}>STOP</div>
            <div style={{ fontSize: 11, color: C.red, fontWeight: 500 }}>{fmtMoney(result.stop, currency)}</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 7, color: C.textMuted, letterSpacing: 1 }}>TP2</div>
            <div style={{ fontSize: 11, color: C.green, fontWeight: 500 }}>{fmtMoney(result.tp2, currency)}</div>
          </div>
        </div>
      )}

      {/* Risk/Reward + Position */}
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: C.textDim }}>
        <span>R/R: <span style={{ color: C.text }}>{fmtRatio(result.risk_reward)}</span></span>
        {result.max_position_pct != null && (
          <span>Max Pos: <span style={{ color: C.text }}>{Number(result.max_position_pct).toFixed(1)}%</span></span>
        )}
        {result.suggested_quantity > 0 && (
          <span>Qty: <span style={{ color: C.text }}>{result.suggested_quantity}</span></span>
        )}
      </div>

      {/* Validations summary */}
      {result.validations && (
        <div style={{ marginTop: 4, fontSize: 8, color: C.textMuted }}>
          Validations: {result.confirmations_passed || 0}/{result.confirmations_total || Object.keys(result.validations).length} passed
        </div>
      )}

      {/* LLM Advisor overlay */}
      {result.advisor_score != null && !isNaN(parseFloat(result.advisor_score)) && (() => {
        const score = parseFloat(result.advisor_score);
        const barColor = score >= 0 ? C.green : C.red;
        const pct = Math.round(((score + 1) / 2) * 100);
        return (
          <div style={{ marginTop: 10, padding: "8px 10px", background: C.bgDeep, borderRadius: 4, border: `1px solid ${C.borderHi}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
              <span style={{ fontSize: 8, color: C.textMuted, letterSpacing: "0.1em" }}>LLM ADVISOR</span>
              <span style={{ fontSize: 11, color: barColor, fontWeight: 700 }}>
                {score >= 0 ? "+" : ""}{score.toFixed(2)}
              </span>
            </div>
            <div style={{ position: "relative", height: 4, background: C.border, borderRadius: 2, marginBottom: 5 }}>
              <div style={{ position: "absolute", left: "50%", top: 0, width: 1, height: "100%", background: C.borderHi }} />
              <div style={{
                position: "absolute",
                left: score >= 0 ? "50%" : `${pct}%`,
                width: `${Math.abs(score) * 50}%`,
                height: "100%",
                background: barColor,
                borderRadius: 2,
                opacity: 0.9,
              }} />
            </div>
            {result.advisor_rationale && (
              <div style={{
                fontSize: 9,
                color: C.textDim,
                lineHeight: 1.5,
                display: "-webkit-box",
                WebkitLineClamp: 3,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
              }}>
                {result.advisor_rationale}
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}