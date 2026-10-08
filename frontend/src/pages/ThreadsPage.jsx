import React, { useState } from "react";
import { useSimulationSocket } from "../hooks/useSimulationSocket.js";
import ModeFrame from "../components/ModeFrame.jsx";
import UtilizationPanel from "../components/UtilizationPanel.jsx";
import ComparisonPanel from "../components/ComparisonPanel.jsx";
import SimControls from "../components/SimControls.jsx";
import { WS_BASE } from "../api.js";

export default function ThreadsPage() {
  const [focus, setFocus] = useState(null);

  const { data: multiData, connected: multiConnected } = useSimulationSocket(
    `${WS_BASE}/ws/simulation`
  );
  const { data: monoData, connected: monoConnected } = useSimulationSocket(
    `${WS_BASE}/ws/simulation-mono`
  );

  const toggleFocus = (mode) => {
    setFocus((f) => (f === mode ? null : mode));
  };

  return (
    <>
      <header className="app-header stage-header">
        <h1>Threads</h1>
        <div className="stage-controls">
          <SimControls
            controlPath="/api/threads/control"
            status={multiData?.status}
            connected={multiConnected && monoConnected}
          />
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
    </>
  );
}
