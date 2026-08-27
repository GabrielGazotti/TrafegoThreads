import React from "react";

function chaosLabel(level) {
  if (level < 20) return { text: "CALMO", cls: "chaos-calm" };
  if (level < 45) return { text: "MOVIMENTADO", cls: "chaos-moderate" };
  if (level < 70) return { text: "CAÓTICO", cls: "chaos-high" };
  return { text: "CAOS TOTAL", cls: "chaos-extreme" };
}

export default function ChaosIndicator({ level = 0 }) {
  const { text, cls } = chaosLabel(level);
  return (
    <div className={`chaos-indicator ${cls}`}>
      <div className="chaos-bar-track">
        <div className="chaos-bar-fill" style={{ width: `${Math.min(100, level)}%` }} />
      </div>
      <div className="chaos-text">
        <span className="chaos-emoji">{level >= 70 ? "🔥" : level >= 45 ? "⚠️" : level >= 20 ? "🚦" : "✅"}</span>
        {text} ({level})
      </div>
    </div>
  );
}
