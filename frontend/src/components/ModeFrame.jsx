import React from "react";
import CityMap from "./CityMap.jsx";
import ThreadStrip from "./ThreadStrip.jsx";

export default function ModeFrame({
  mode,
  label,
  data,
  connected,
  highlighted = false,
  onFocus,
}) {
  const vehicles = data?.vehicles || [];
  const intersections = data?.intersections || [];
  const metrics = data?.metrics;
  const tickingId = data?.ticking_id ?? null;
  const simultaneous = data?.utilization?.simultaneous_intersections ?? 0;
  const peakThreads = metrics?.peak_threads ?? 0; 

  return (
    <div className={`mode-frame mode-${mode} ${highlighted ? "mode-focused" : ""}`}>
      <div className="mode-frame-header">
        <span className={`mode-chip chip-${mode}`}>{label}</span>
        {simultaneous > 0 && (
          <span className="simultaneous-badge" title="Cruzamentos com 2+ veículos">
            2+ ×{simultaneous}
          </span>
        )}
        <span className={`conn-dot ${connected ? "conn-ok" : "conn-down"}`} title={connected ? "ok" : "…"} />
        {onFocus && (
          <button type="button" className="focus-btn" onClick={onFocus} title="Focar">
            ⛶
          </button>
        )}
      </div>
      <CityMap vehicles={vehicles} intersections={intersections} />
      <ThreadStrip
        mode={mode}
        vehicles={vehicles}
        activeThreads={metrics?.active_threads ?? 0}
        peakThreads={peakThreads}
        tickingId={tickingId}
      />
    </div>
  );
}
