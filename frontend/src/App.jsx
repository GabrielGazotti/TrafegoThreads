import React, { useCallback, useState } from "react";
import { useSimulationSocket } from "./hooks/useSimulationSocket.js";
import ModeFrame from "./components/ModeFrame.jsx";
import UtilizationPanel from "./components/UtilizationPanel.jsx";
import ComparisonPanel from "./components/ComparisonPanel.jsx";

const API_BASE = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;
const WS_BASE = import.meta.env.VITE_WS_URL?.replace(/\/ws\/.*$/, "") || `ws://${window.location.hostname}:8000`;

export default function App() {
  const [focus, setFocus] = useState(null);

  const { data: multiData, connected: multiConnected } = useSimulationSocket(
    `${WS_BASE}/ws/simulation`
  );
  const { data: monoData, connected: monoConnected } = useSimulationSocket(
    `${WS_BASE}/ws/simulation-mono`
  );

  const reset = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/api/reset`, { method: "POST" });
    } catch {
      /* ignore */
    }
  }, []);

  const toggleFocus = (mode) => {
    setFocus((f) => (f === mode ? null : mode));
  };

  const bothConnected = multiConnected && monoConnected;

  return (
    <div className="app app-stage">
      <header className="app-header stage-header">
        <h1>Trânsito — MULTI vs MONO</h1>
        <div className="stage-controls">
          <button type="button" className="reset-btn" onClick={reset} title="Reset">
            ↺
          </button>
        </div>
      </header>

      <UtilizationPanel multiData={multiData} monoData={monoData} />
      <ComparisonPanel multiData={multiData} monoData={monoData} />

      <div className={`stage-grid ${focus ? `focus-${focus}` : ""}`}>
        <ModeFrame
          mode="multi"
          label="MULTI"
          data={multiData}
          connected={multiConnected}
          highlighted={focus === "multi"}
          onFocus={() => toggleFocus("multi")}
        />
        <ModeFrame
          mode="mono"
          label="MONO"
          data={monoData}
          connected={monoConnected}
          highlighted={focus === "mono"}
          onFocus={() => toggleFocus("mono")}
        />
      </div>
    </div>
  );
}
