import React from "react";
import { useSimulationSocket } from "./hooks/useSimulationSocket.js";
import CityMap from "./components/CityMap.jsx";
import MetricsPanel from "./components/MetricsPanel.jsx";
import EventLog from "./components/EventLog.jsx";
import ChaosIndicator from "./components/ChaosIndicator.jsx";
import Legend from "./components/Legend.jsx";

export default function App() {
  const { data, connected } = useSimulationSocket();

  const vehicles = data?.vehicles || [];
  const intersections = data?.intersections || [];
  const metrics = data?.metrics;
  const chaos = data?.chaos ?? 0;
  const events = data?.events || [];

  return (
    <div className="app">
      <header className="app-header">
        <h1>🚦 Simulador de Trânsito — Versão SEM Sincronização</h1>
        <span className={`conn-badge ${connected ? "conn-ok" : "conn-down"}`}>
          {connected ? "● WebSocket conectado" : "○ Reconectando…"}
        </span>
      </header>

      <p className="app-subtitle">
        Cada veículo roda em sua própria <code>Thread</code>. Não há <code>Lock</code>,{" "}
        <code>Semaphore</code> ou fila global — vários veículos podem entrar no mesmo
        cruzamento ao mesmo tempo, gerando conflitos e colisões de propósito.
      </p>

      <ChaosIndicator level={chaos} />

      <div className="main-grid">
        <div className="map-column">
          <CityMap vehicles={vehicles} intersections={intersections} />
          <Legend />
        </div>

        <div className="side-column">
          <h2>Métricas</h2>
          <MetricsPanel metrics={metrics} />

          <h2>Log de eventos</h2>
          <EventLog events={events} />
        </div>
      </div>
    </div>
  );
}
