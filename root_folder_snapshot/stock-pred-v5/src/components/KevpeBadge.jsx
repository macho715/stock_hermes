import React from "react";

const C = {
  green: "#00FF88",
  amber: "#FFB800",
  red: "#FF3366",
  textDim: "#6B7E8E",
  textMuted: "#3F5060",
  panel: "#0A1218",
};

const FONT = '"JetBrains Mono","Fira Code",ui-monospace,SFMono-Regular,Menlo,monospace';

const REGIME_CONFIG = {
  GREEN: { label: "GREEN", color: C.green, bg: "rgba(0,255,136,0.1)" },
  AMBER: { label: "AMBER", color: C.amber, bg: "rgba(255,184,0,0.1)" },
  RED: { label: "RED", color: C.red, bg: "rgba(255,51,102,0.1)" },
};

const CONFIDENCE_COLOR = {
  high: C.green,
  medium: C.amber,
  low: C.red,
};

export default function KevpeBadge({ result, size = 9 }) {
  if (!result || result.kevpe_available !== true) {
    return null;
  }

  const regime = result.kevpe_regime || "AMBER";
  const regimeConf = REGIME_CONFIG[regime] || REGIME_CONFIG.AMBER;
  const confidence = result.kevpe_confidence || "medium";
  const confColor = CONFIDENCE_COLOR[confidence] || C.amber;
  const score = typeof result.kevpe_score === "number" ? result.kevpe_score.toFixed(2) : "—";
  const expected = typeof result.kevpe_expected_return_pct === "number" ? `${result.kevpe_expected_return_pct > 0 ? "+" : ""}${result.kevpe_expected_return_pct.toFixed(1)}%` : "—";
  const ciLow = Array.isArray(result.kevpe_ci) ? result.kevpe_ci[0] : null;
  const ciHigh = Array.isArray(result.kevpe_ci) ? result.kevpe_ci[1] : null;
  const ciStr = ciLow != null && ciHigh != null ? `[${ciLow.toFixed(1)}, ${ciHigh.toFixed(1)}]` : null;

  return (
    <div style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 5,
      padding: "2px 6px",
      background: C.panel,
      border: `1px solid ${regimeConf.color}44`,
      borderRadius: 3,
      fontFamily: FONT,
      fontSize: size,
    }}>
      <span
        style={{
          padding: "1px 4px",
          fontWeight: 700,
          letterSpacing: 1,
          color: regimeConf.color,
          background: regimeConf.bg,
          border: `1px solid ${regimeConf.color}55`,
          borderRadius: 2,
        }}
      >
        KEVPE {regimeConf.label}
      </span>

      <span style={{ color: confColor, fontWeight: 600, letterSpacing: 0.5 }}>
        {score}
      </span>

      <span style={{ color: C.textDim }}>
        E[RV]={expected}
      </span>

      {ciStr && (
        <span style={{ color: C.textMuted }}>
          CI {ciStr}
        </span>
      )}

      <span style={{ color: confColor, fontSize: size - 1 }}>
        {confidence.toUpperCase()}
      </span>
    </div>
  );
}
