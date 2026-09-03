import React from "react";

function Metric({ label, value, highlight }) {
  return (
    <div className={`metric ${highlight ? "metric-highlight" : ""}`}>
      <span className="metric-value">{value}</span>
      <span className="metric-label">{label}</span>
    </div>
  );
}

export default function MetricsPanel({ metrics }) {
  if (!metrics) return null;

  return (
    <div className="metrics-panel">
      <Metric label="Veículos ativos" value={metrics.vehicles_alive} />
      <Metric label="Veículos criados" value={metrics.vehicles_total} />
      <Metric label="Threads ativas" value={metrics.active_threads} highlight />
      <Metric label="Aguardando" value={metrics.vehicles_waiting} />
      <Metric label="Colisões" value={metrics.collisions} highlight />
      <Metric label="Race (cruzamento)" value={metrics.intersection_conflicts} highlight />
      <Metric label="Espera média (s)" value={metrics.average_wait_time} />
      <Metric label="Eventos processados" value={metrics.events_processed} />
      <Metric label="Tempo de execução (s)" value={metrics.uptime} />
    </div>
  );
}
