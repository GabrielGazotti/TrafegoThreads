import React, { useCallback, useEffect, useState } from "react";
import { useSimulationSocket } from "../hooks/useSimulationSocket.js";
import CityMap from "../components/CityMap.jsx";
import ThreadStrip from "../components/ThreadStrip.jsx";
import SimControls from "../components/SimControls.jsx";
import SchedulerControls, { Segmented } from "../components/SchedulerControls.jsx";
import CompareView from "../components/CompareView.jsx";
import MetricHighlights from "../components/MetricHighlights.jsx";
import ModeComparisonTable from "../components/ModeComparisonTable.jsx";
import { highlightRows, phaseColumns } from "../components/SyncMetricsPanel.jsx";
import { API_BASE, WS_BASE } from "../api.js";
import "../scheduling.css";

const VIEW_KEY = "sched-view";
const VIEWS = [
  { key: "compare", label: "Comparação", title: "Vários escalonadores ao mesmo tempo, com o mesmo tráfego" },
  { key: "single", label: "Individual", title: "Uma simulação, trocando semáforo e escalonador ao vivo" },
];
const PANELS = [
  { key: "map", label: "🗺 Mapa" },
  { key: "table", label: "📊 Tabela" },
];

function loadView() {
  try {
    return localStorage.getItem(VIEW_KEY) === "single" ? "single" : "compare";
  } catch {
    return "compare";
  }
}

function saveView(view) {
  try {
    localStorage.setItem(VIEW_KEY, view);
  } catch {
    // sem storage: só não lembra a escolha
  }
}

/** Tela cheia do navegador (F11 programático); acompanha o Esc do usuário. */
function useFullscreen() {
  const [active, setActive] = useState(() => Boolean(document.fullscreenElement));
  useEffect(() => {
    const onChange = () => setActive(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);
  const toggle = useCallback(() => {
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
    else document.documentElement.requestFullscreen?.().catch(() => {});
  }, []);
  return [active, toggle];
}

/** Modo individual: uma simulação, semáforo e escalonador trocados ao vivo. */
function SingleView({ nav }) {
  const { data, connected } = useSimulationSocket(`${WS_BASE}/ws/scheduling`);
  const [pending, setPending] = useState(false);
  const [panel, setPanel] = useState("map");

  const syncEnabled = data?.sync_enabled ?? false;
  const algorithm = data?.algorithm;
  const vehicles = data?.vehicles || [];
  const metrics = data?.metrics;
  const emergencies = vehicles.filter((v) => v.emergency && !v.crashed && v.state !== "finished").length;
  const laneKey = syncEnabled ? (algorithm?.name ?? "fixed") : "off";

  const toggleSync = useCallback(async () => {
    setPending(true);
    try {
      await fetch(`${API_BASE}/api/scheduling/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !syncEnabled }),
      });
    } catch {
      // o próximo frame do WebSocket mostra o estado real
    } finally {
      setPending(false);
    }
  }, [syncEnabled]);

  const columns = phaseColumns(metrics);

  return (
    <>
      <div className="sc-bar">
        {nav}
        <span className="sc-sep" />
        <button
          type="button"
          className={`sync-btn ${syncEnabled ? "sync-on" : "sync-off"}`}
          onClick={toggleSync}
          disabled={pending || !connected}
        >
          <span className="sync-light" />
          Semáforo {syncEnabled ? "ON" : "OFF"}
        </button>
        <SchedulerControls
          algorithm={algorithm}
          syncEnabled={syncEnabled}
          emergencyRate={data?.emergency_rate}
          connected={connected}
        />
        <span className="sc-spacer" />
        <Segmented options={PANELS} value={panel} onChange={setPanel} />
        <SimControls controlPath="/api/scheduling/control" status={data?.status} connected={connected} />
      </div>

      {panel === "table" ? (
        <main className="sc-main sc-main-table">
          <ModeComparisonTable columns={columns} />
        </main>
      ) : (
        <>
          <MetricHighlights rows={highlightRows(metrics)} />
          <main className="sc-main lane-grid lane-grid-1">
            <section className={`lane-card lane-${laneKey}`}>
              <header className="lane-head">
                <span className="lane-dot" />
                <span className="lane-title">
                  {syncEnabled ? algorithm?.label ?? "Semáforo ON" : "Semáforo OFF"}
                </span>
                <span className={`lane-sync ${syncEnabled ? "lane-sync-on" : ""}`}>
                  {syncEnabled ? "COM SYNC" : "SEM SYNC"}
                </span>
                <span className="lane-live" title="Emergências ativas · veículos parados">
                  🚑 {emergencies} · ⏳ {metrics?.vehicles_waiting ?? 0}
                </span>
                <span className={`conn-dot ${connected ? "conn-ok" : "conn-down"}`} title={connected ? "conectado" : "sem conexão"} />
              </header>
              <div className="lane-map">
                <CityMap
                  vehicles={vehicles}
                  intersections={data?.intersections || []}
                  signals={syncEnabled ? "on" : "off"}
                  lanes
                  vehicleSize={22}
                  configPath="/api/scheduling/config"
                />
              </div>
              <ThreadStrip
                mode="multi"
                vehicles={vehicles}
                activeThreads={metrics?.active_threads ?? 0}
                peakThreads={metrics?.peak_threads ?? 0}
              />
            </section>
          </main>
        </>
      )}
    </>
  );
}

export default function SchedulingPage() {
  const [view, setView] = useState(loadView);
  const [fullscreen, toggleFullscreen] = useFullscreen();

  const choose = (v) => {
    setView(v);
    saveView(v);
  };

  const nav = (
    <div className="sc-group">
      <Segmented options={VIEWS} value={view} onChange={choose} className="sc-views" />
      <button
        type="button"
        className="sc-fs-btn"
        onClick={toggleFullscreen}
        title={fullscreen ? "Sair da tela cheia (Esc)" : "Tela cheia para apresentar"}
        aria-label="Tela cheia"
      >
        {fullscreen ? "✕ Sair da tela cheia" : "⛶ Tela cheia"}
      </button>
    </div>
  );

  return (
    <div className={`sc-page ${fullscreen ? "sc-fullscreen" : ""}`}>
      {view === "compare" ? <CompareView nav={nav} /> : <SingleView nav={nav} />}
    </div>
  );
}
