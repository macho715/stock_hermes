import React from "react";

const C = {
  green: "#00FF88",
  amber: "#FFB800",
  red: "#FF3366",
  gray: "#3F5060",
};

const VERDICT_CONFIG = {
  ELIGIBLE_RECOMMENDATION: { label: "ELIGIBLE", color: C.green, bg: "rgba(0,255,136,0.1)" },
  ACCUMULATE_RECOMMENDATION: { label: "ACCUMULATE", color: C.green, bg: "rgba(0,255,136,0.1)" },
  AMBER_REVIEW_ONLY: { label: "AMBER", color: C.amber, bg: "rgba(255,184,0,0.1)" },
  AMBER_WATCHLIST: { label: "AMBER", color: C.amber, bg: "rgba(255,184,0,0.1)" },
  RED_BELOW_THRESHOLD: { label: "RED", color: C.red, bg: "rgba(255,51,102,0.1)" },
  RED_DATA_OR_MODEL_ERROR: { label: "RED", color: C.red, bg: "rgba(255,51,102,0.1)" },
  ZERO_RISK_PLAN_FAILED: { label: "ZERO", color: C.gray, bg: "rgba(63,80,96,0.15)" },
  ZERO_NO_DATA: { label: "ZERO", color: C.gray, bg: "rgba(63,80,96,0.15)" },
};

export default function RiskGateBadge({ verdict, size = 11 }) {
  const config = VERDICT_CONFIG[verdict] || { label: verdict || "N/A", color: C.gray, bg: "rgba(63,80,96,0.1)" };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 6px",
        fontSize: size,
        fontWeight: 700,
        letterSpacing: 1.5,
        color: config.color,
        background: config.bg,
        border: `1px solid ${config.color}55`,
        borderRadius: 3,
        fontFamily: '"JetBrains Mono","Fira Code",ui-monospace,monospace',
        whiteSpace: "nowrap",
      }}
    >
      {config.label}
    </span>
  );
}