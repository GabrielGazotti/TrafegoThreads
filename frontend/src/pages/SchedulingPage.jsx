import React, { useCallback, useState } from "react";
import { useSimulationSocket } from "../hooks/useSimulationSocket.js";
import CityMap from "../components/CityMap.jsx";
import ThreadStrip from "../components/ThreadStrip.jsx";
import SyncMetricsPanel from "../components/SyncMetricsPanel.jsx";
import SimControls from "../components/SimControls.jsx";
import { API_BASE, WS_BASE } from "../api.js";

export default function SchedulingPage() {
  const { data, connected } = useSimulationSocket(`${WS_BASE}/ws/scheduling`);
  const [pending, setPending] = useState(false);

  const syncEnabled = data?.sync_enabled ?? false;
  const vehicles = data?.vehicles || [];
  const metrics = data?.metrics;
  const emergencies = vehicles.filter(
    (v) => v.emergency && !v.crashed && v.state !== "finished"
  ).length;

  const toggleSync = useCallback(async () => {
    setPending(true);
    try {
      await fetch(`${API_BASE}/api/scheduling/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !syncEnabled }),
      });
    } catch {

    } finally {
      setPending(false);
    }
  }, [syncEnabled]);

  return (
    <>
      <header className="app-header stage-header">
        <h1>Sincronismo e Scheduling</h1>
        <div className="stage-controls">
          <button
            type="button"
            className={`sync-btn ${syncEnabled ? "sync-on" : "sync-off"}`}
            onClick={toggleSync}
            disabled={pending || !connected}
          >
            <span className="sync-light" />
            Semáforo {syncEnabled ? "ON" : "OFF"}
          </button>
          <SimControls
            controlPath="/api/scheduling/control"
            status={data?.status}
            connected={connected}
          />
        </div>
      </header>

      <SyncMetricsPanel metrics={metrics} />

      <div className="stage-grid sched-grid">
        <div className="mode-frame mode-multi">
          <div className="mode-frame-header">
            <span className="mode-chip chip-multi">MULTI</span>
            <span className={`mode-chip ${syncEnabled ? "chip-sync-on" : "chip-sync-off"}`}>
              {syncEnabled ? "COM SYNC" : "SEM SYNC"}
            </span>
            {emergencies > 0 && (
              <span className="emergency-badge" title="Veículos de emergência ativos">
                🚨 ×{emergencies}
              </span>
            )}
            <span
              className={`conn-dot ${connected ? "conn-ok" : "conn-down"}`}
              title={connected ? "ok" : "…"}
            />
          </div>
          <CityMap
            vehicles={vehicles}
            intersections={data?.intersections || []}
            signals={syncEnabled ? "on" : "off"}
            lanes
            configPath="/api/scheduling/config"
          />
          <ThreadStrip
            mode="multi"
            vehicles={vehicles}
            activeThreads={metrics?.active_threads ?? 0}
            peakThreads={metrics?.peak_threads ?? 0}
          />
        </div>
      </div>
    </>
  );
}
