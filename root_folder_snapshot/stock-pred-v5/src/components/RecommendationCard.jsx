import React from "react";
import RiskGateBadge from "./RiskGateBadge";
import KevpeBadge from "./KevpeBadge";

// ---------------------------------------------------------------------------
// Regime badge — [Wave 4 Dashboard] MacroRegime LLM label
// ---------------------------------------------------------------------------
const REGIME_CFG = {
  risk_on:  { bg: "#00FF8822", color: "#00FF88", label: "RISK ON ↑"  },
  neutral:  { bg: "#3F506044", color: "#8899AA", label: "NEUTRAL —"  },
  risk_off: { bg: "#FF336622", color: "#FF3366", label: "RISK OFF ↓" },
};
const REGIME_TIP = "Market regime from LLM MacroRegime advisor. risk_on=bullish macro, neutral=mixed, risk_off=bearish macro.";

function RegimeBadge({ regime }) {
  if (!regime) return null;
  const cfg = REGIME_CFG[regime];
  if (!cfg) return null;
  return (
    <div title={REGIME_TIP} style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 6 }}>
      <span style={{ fontSize: 8, color: C.textMuted, letterSpacing: 1 }}>REGIME</span>
      <span style={{
        background: cfg.bg, color: cfg.color,
        borderRadius: 3, padding: "1px 7px",
        fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.03em",
      }}>{cfg.label}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Model scores strip — [Wave 4 Dashboard] main_prob + tft_prob
// ---------------------------------------------------------------------------
function ModelScoresStrip({ mainProb, tftProb, modelKind }) {
  if (mainProb == null && tftProb == null) return null;
  const isStub = tftProb != null && Math.abs(tftProb - 0.5) < 0.001;
  const probColor = (p) => p == null ? C.textMuted : p >= 0.56 ? C.green : p <= 0.44 ? C.red : C.textDim;
  return (
    <div style={{ display: "flex", gap: 12, marginTop: 5, fontSize: 8, color: C.textDim, letterSpacing: 0.5 }}>
      {mainProb != null && (
        <span>
          {modelKind ? <span style={{ color: C.textMuted }}>{String(modelKind).toUpperCase().slice(0,3)} </span> : "MAIN "}
          <b style={{ color: probColor(mainProb) }}>{Number(mainProb).toFixed(2)}</b>
        </span>
      )}
      {tftProb != null && (
        <span title={isStub ? "TFT stub — pytorch_forecasting not installed" : "TFT model score"}>
          TFT{" "}
          <b style={{ color: isStub ? C.textMuted : probColor(tftProb) }}>
            {Number(tftProb).toFixed(2)}{isStub ? "*" : ""}
          </b>
        </span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PBO badge — [E2 Wave 3]
// ---------------------------------------------------------------------------
const PBO_CFG = {
  PASS:    { bg: "#22c55e", color: "#fff", label: "PASS",  icon: "✓" },
  AMBER:   { bg: "#f59e0b", color: "#000", label: "AMBER", icon: "⚠" },
  RED:     { bg: "#ef4444", color: "#fff", label: "RED",   icon: "✕" },
  NO_DATA: { bg: "#4b5563", color: "#fff", label: "N/A",   icon: "–" },
};
const PBO_TIP = "Probability of Backtest Overfitting (PBO). Lower = better. ≤20% PASS · ≤50% AMBER · >50% RED.";

function PboBadge({ pbo, pboStatus }) {
  const cfg = PBO_CFG[pboStatus] ?? PBO_CFG.NO_DATA;
  const txt = pbo != null ? `${(Number(pbo) * 100).toFixed(1)}%` : "–";
  return (
    <div title={PBO_TIP} role="img" aria-label={`PBO ${txt} ${cfg.label}`}
      style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 4 }}>
      <span style={{ fontSize: "0.7rem", color: "#6B7E8E", letterSpacing: 1 }}>PBO</span>
      <span style={{ fontSize: "0.7rem", color: "#D4E1EC" }}>{txt}</span>
      <span style={{
        background: cfg.bg, color: cfg.color,
        borderRadius: 3, padding: "1px 5px",
        fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.03em",
      }}>{cfg.icon} {cfg.label}</span>
    </div>
  );
}

const SIZING_CFG = {
  PASS: { color: "#00FF88" },
  AMBER: { color: "#FFB800" },
  ZERO: { color: "#FF3366" },
  NO_DATA: { color: "#6B7E8E" },
};

function SizingBadge({ result }) {
  const strategy = result?.sizing_strategy_used;
  if (!strategy || strategy === "off" || result?.size_multiplier == null) return null;
  const status = result.sizing_coverage_status || "NO_DATA";
  const cfg = SIZING_CFG[status] ?? SIZING_CFG.NO_DATA;
  const mult = Number(result.size_multiplier);
  return (
    <div title="CMRS sizing is downgrade-only and report-only." style={{
      display: "grid",
      gridTemplateColumns: "repeat(3, auto)",
      gap: 6,
      marginTop: 6,
      alignItems: "center",
      fontSize: 8,
      color: C.textDim,
      letterSpacing: 0.8,
    }}>
      <span>SIZE <b style={{ color: C.text }}>{Number.isFinite(mult) ? mult.toFixed(3) : "N/A"}</b></span>
      <span>SIZER <b style={{ color: C.text }}>{strategy}</b></span>
      <span>COVERAGE <b style={{ color: cfg.color }}>{status}</b></span>
    </div>
  );
}

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

function isSourceConflict(result) {
  const status = String(
    result?.investment_readiness_status
    || result?.dashboard_status
    || result?.readiness_status
    || ""
  );
  return status === "AMBER_SOURCE_CONFLICT";
}

function badgeColor(label) {
  const text = String(label || "").toUpperCase();
  if (text.includes("MODEL") || text.includes("SOURCE") || text.includes("STATIC")) return C.amber;
  if (text.includes("BACKTEST") || text.includes("BLOCK") || text.includes("INSUFFICIENT")) return C.red;
  return C.textDim;
}

function SourceConflictChip({ label, color }) {
  return (
    <span style={{
      color,
      border: `1px solid ${color}77`,
      background: `${color}14`,
      padding: "2px 6px",
      borderRadius: 3,
      fontSize: "0.62rem",
      fontWeight: 700,
      letterSpacing: "0.04em",
      lineHeight: 1.45,
      whiteSpace: "normal",
    }}>
      {label}
    </span>
  );
}

function SourceConflictBanner({ result }) {
  const badges = Array.isArray(result?.display_badges) ? result.display_badges : [];
  const reasons = Array.isArray(result?.blocking_reasons) ? result.blocking_reasons : [];
  const capitalBlocked = result?.new_capital_allowed === false;
  const brokerBlocked = result?.safety_flags?.broker_order_execution === false || result?.broker_order_execution === false;
  const paperOnly = result?.paper_recording_allowed === true || result?.paper_trading_only === true;

  return (
    <div style={{
      marginBottom: 10,
      padding: "10px",
      background: "#241104",
      border: `1px solid ${C.amber}`,
      borderLeft: `4px solid ${C.red}`,
      borderRadius: 4,
    }}>
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 6, marginBottom: 7 }}>
        <span style={{
          color: "#050A0E",
          background: C.amber,
          borderRadius: 3,
          padding: "3px 7px",
          fontSize: "0.65rem",
          fontWeight: 800,
          letterSpacing: "0.06em",
          lineHeight: 1.35,
        }}>
          AMBER_SOURCE_CONFLICT
        </span>
        <SourceConflictChip label="LIVE REVIEW BLOCKED" color={C.red} />
        {paperOnly && <SourceConflictChip label="PAPER RECORDING ONLY" color={C.amber} />}
        {capitalBlocked && <SourceConflictChip label="NEW CAPITAL BLOCKED" color={C.red} />}
        {brokerBlocked && <SourceConflictChip label="NO BROKER EXECUTION" color={C.amber} />}
      </div>
      <div style={{ color: C.text, fontSize: "0.72rem", lineHeight: 1.5, fontWeight: 700 }}>
        Signal, recommendation, and backtest evidence are not aligned.
      </div>
      <div style={{ color: C.textDim, fontSize: "0.67rem", lineHeight: 1.5, marginTop: 2 }}>
        This candidate is blocked from live review. Score remains visible for audit only.
      </div>
      {badges.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginTop: 8 }}>
          {badges.map((badge) => (
            <span key={badge} style={{
              color: badgeColor(badge),
              border: `1px solid ${badgeColor(badge)}66`,
              background: `${badgeColor(badge)}18`,
              padding: "2px 6px",
              borderRadius: 3,
              fontSize: "0.6rem",
              fontWeight: 700,
              letterSpacing: "0.04em",
              lineHeight: 1.45,
              overflowWrap: "anywhere",
            }}>
              {badge}
            </span>
          ))}
        </div>
      )}
      {reasons.length > 0 && (
        <details style={{ marginTop: 8 }}>
          <summary style={{ color: C.text, cursor: "pointer", fontSize: "0.65rem", minHeight: 28, lineHeight: "28px" }}>
            Blocking reasons ({reasons.length})
          </summary>
          <div style={{ display: "grid", gap: 3, marginTop: 4 }}>
            {reasons.map((reason) => (
              <div key={reason} style={{ color: C.textDim, fontSize: "0.6rem", lineHeight: 1.45, overflowWrap: "anywhere" }}>
                {reason}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

export default function RecommendationCard({ result, currency = "$", accent = "#00CCFF", onClick }) {
  if (!result) return null;
  const isGreen = result.verdict?.includes("ELIGIBLE") || result.verdict?.includes("ACCUMULATE");
  const isAmber = result.verdict?.includes("AMBER");
  const isRed = result.verdict?.startsWith("RED") || result.verdict?.startsWith("ZERO");
  const sourceConflict = isSourceConflict(result);
  const borderColor = sourceConflict ? C.red : isGreen ? C.green : isAmber ? C.amber : isRed ? C.red : C.border;

  return (
    <div
      onClick={onClick}
      style={{
        background: C.panel,
        border: `1px solid ${borderColor}44`,
        borderLeft: `3px solid ${borderColor}`,
        borderRadius: 6,
        padding: "12px 14px",
        marginBottom: 10,
        cursor: onClick ? "pointer" : "default",
        transition: "background .15s, box-shadow .15s",
        boxShadow: `0 2px 8px rgba(0,0,0,0.4), inset 0 1px 0 ${borderColor}22`,
      }}
      onMouseEnter={(e) => {
        if (onClick) {
          e.currentTarget.style.background = C.panel2;
          e.currentTarget.style.boxShadow = `0 4px 16px rgba(0,0,0,0.5), inset 0 1px 0 ${borderColor}33`;
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = C.panel;
        e.currentTarget.style.boxShadow = `0 2px 8px rgba(0,0,0,0.4), inset 0 1px 0 ${borderColor}22`;
      }}
    >
      {sourceConflict && <SourceConflictBanner result={result} />}

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 16, fontWeight: 800, color: accent, letterSpacing: "0.12em" }}>
            {result.ticker?.replace(".KS", "") || result.rank + "."}
          </span>
          <RiskGateBadge verdict={result.verdict} size={9} />
          <KevpeBadge result={result} size={8} />
        </div>
        {/* Score pill */}
        <div style={{
          background: `${borderColor}22`,
          border: `1px solid ${borderColor}66`,
          borderRadius: 4,
          padding: "3px 10px",
          textAlign: "center",
          minWidth: 44,
        }}>
          <div style={{ fontSize: 20, fontWeight: 800, color: borderColor, lineHeight: 1.1 }}>
            {result.score != null ? Math.round(result.score) : "—"}
          </div>
          <div style={{ fontSize: 7, color: C.textMuted, letterSpacing: "0.12em", marginTop: 1 }}>SCORE</div>
        </div>
      </div>

      {/* Track + Probability */}
      <div style={{ display: "flex", gap: 12, marginBottom: 6, fontSize: 9, color: C.textDim }}>
        <span style={{ color: result.track === "S" ? C.us : C.krx, fontWeight: 600, letterSpacing: 1 }}>
          Track-{result.track || "—"}
        </span>
        <span style={{ color: sourceConflict ? C.red : C.textDim, fontWeight: sourceConflict ? 700 : 400 }}>
          {result.investment_readiness_status || result.dashboard_status || result.readiness_status || "REPORT ONLY"}
        </span>
        {result.new_capital_allowed === false && (
          <span style={{ color: C.red }}>New capital blocked</span>
        )}
        {(result.paper_recording_allowed === true || result.paper_trading_only === true) && (
          <span style={{ color: C.amber }}>Paper recording only</span>
        )}
        {(result.safety_flags?.broker_order_execution === false || result.broker_order_execution === false) && (
          <span style={{ color: C.amber }}>No broker execution</span>
        )}
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
          gap: 4, padding: "8px 10px",
          background: C.bgDeep, borderRadius: 4,
          border: `1px solid ${C.border}`,
          marginBottom: 6,
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

      {/* [E2] PBO badge */}
      {(() => {
        const bhs = result.backtest_honesty_summary;
        if (!bhs || bhs.pbo_status == null) return null;
        return <PboBadge pbo={bhs.pbo} pboStatus={bhs.pbo_status} />;
      })()}

      <SizingBadge result={result} />

      {/* [Wave 4] Regime badge */}
      <RegimeBadge regime={result.advisor_regime} />

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
            {/* [Wave 4] Model scores strip inside advisor section */}
            <ModelScoresStrip
              mainProb={result.direction_prob}
              tftProb={result.tft_prob}
              modelKind={result.model_kind_used}
            />
          </div>
        );
      })()}
    </div>
  );
}
