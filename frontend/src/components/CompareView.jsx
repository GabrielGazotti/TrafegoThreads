import React, { useCallback, useState } from "react";
import { useSimulationSocket } from "../hooks/useSimulationSocket.js";
import { WS_BASE } from "../api.js";
import CityMap from "./CityMap.jsx";
import SimControls from "./SimControls.jsx";
import ModeComparisonTable, { formatMetric } from "./ModeComparisonTable.jsx";
import MetricHighlights from "./MetricHighlights.jsx";
import { EmergencyRateSlider, Segmented, Toggle, post } from "./SchedulerControls.jsx";

const LANES = {
  off: { short: "Semáforo OFF", title: "Sem sincronismo: check-then-act sem lock" },
  fixed: { short: "Ciclo fixo", title: "6 fases sempre na mesma ordem" },
  priority: { short: "Prioridade", title: "Fila de prioridade com preempção / aging" },
  fcfs: { short: "FCFS", title: "Abre a fase de quem chegou primeiro" },
};
const LANE_ORDER = ["off", "fixed", "priority", "fcfs"];

const LANE_KPIS = [
  { key: "collisions", label: "colisões" },
  { key: "average_wait_time_emergency", label: "esp. 🚑", decimals: 1 },
  { key: "average_wait_time_normal", label: "esp. 🚗", decimals: 1 },
  { key: "throughput_per_min", label: "veíc/min", decimals: 1 },
];

const PANELS = [
  { key: "maps", label: "🗺 Mapas" },
  { key: "table", label: "📊 Tabela" },
];

const commitRate = (rate) => post("/api/scheduling/compare/config", { emergency_rate: rate });

function clock(seconds = 0) {
  const s = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

function LaneCard({ lane }) {
  const vehicles = lane.vehicles || [];
  const emergencies = vehicles.filter((v) => v.emergency && !v.crashed && v.state !== "finished").length;
  const waiting = lane.metrics?.vehicles_waiting ?? 0;
  const sync = lane.sync_enabled;
  return (
    <section className={`lane-card lane-${lane.key}`}>
      <header className="lane-head">
        <span className="lane-dot" />
        <span className="lane-title" title={LANES[lane.key]?.title}>{lane.label}</span>
        <span className={`lane-sync ${sync ? "lane-sync-on" : ""}`}>{sync ? "COM SYNC" : "SEM SYNC"}</span>
        <span className="lane-live" title="Emergências ativas · veículos parados">
          🚑 {emergencies} · ⏳ {waiting}
        </span>
        <div className="lane-kpis">
          {LANE_KPIS.map((k) => (
            <span key={k.key} className="lane-kpi">
              <b>{formatMetric(lane.stats?.[k.key], k.decimals)}</b> {k.label}
            </span>
          ))}
        </div>
      </header>
      <div className="lane-map">
        <CityMap
          vehicles={vehicles}
          intersections={lane.intersections || []}
          signals={sync ? "on" : "off"}
          lanes
          vehicleSize={24}
          configPath="/api/scheduling/config"
        />
      </div>
    </section>
  );
}

export default function CompareView({ nav }) {
  const { data, connected } = useSimulationSocket(`${WS_BASE}/ws/scheduling-compare`);
  const [pending, setPending] = useState(false);
  const [panel, setPanel] = useState("maps");

  const lanes = data?.lanes || [];
  const laneKeys = data?.lane_keys || [];
  const disabled = pending || !connected;

  const configure = useCallback(async (body) => {
    setPending(true);
    await post("/api/scheduling/compare/config", body);
    setPending(false);
  }, []);

  const toggleLane = (key) => {
    const next = laneKeys.includes(key) ? laneKeys.filter((k) => k !== key) : [...laneKeys, key];
    if (next.length >= 2) configure({ lanes: next });
  };

  const rows = lanes.map((l) => ({
    key: l.key,
    label: l.label,
    short: LANES[l.key]?.short,
    laneKey: l.key,
    stats: l.stats,
  }));
  const table = <ModeComparisonTable title="Comparativo — mesmo tráfego, mesmo tempo" columns={rows} />;
  // 3 modos numa grade 2×2: a tabela ocupa o 4º espaço
  const tableInGrid = lanes.length === 3;

  return (
    <>
      <div className="sc-bar">
        {nav}
        <span className="sc-sep" />
        <div className="lane-picker" title="Modos comparados — mudar recomeça a comparação">
          {LANE_ORDER.map((key) => {
            const on = laneKeys.includes(key);
            return (
              <button
                key={key}
                type="button"
                className={`lane-pick lane-${key} ${on ? "lane-pick-on" : ""}`}
                onClick={() => toggleLane(key)}
                disabled={disabled || (on && laneKeys.length <= 2)}
                title={LANES[key].title}
                aria-pressed={on}
              >
                <span className="lane-dot" />
                {LANES[key].short}
              </button>
            );
          })}
        </div>
        {laneKeys.includes("priority") && (
          <div className="sc-group">
            <Toggle
              label="Preempção"
              title="Emergência parada no vermelho corta o verde atual — recomeça a comparação"
              on={data?.preemption ?? true}
              disabled={disabled}
              onClick={() => configure({ preemption: !(data?.preemption ?? true) })}
            />
            <Toggle
              label="Aging"
              title="Prioridade efetiva sobe com a espera — recomeça a comparação"
              on={data?.aging ?? true}
              disabled={disabled}
              onClick={() => configure({ aging: !(data?.aging ?? true) })}
            />
          </div>
        )}
        <EmergencyRateSlider value={data?.emergency_rate} disabled={!connected} onCommit={commitRate} />
        <span className="sc-spacer" />
        <Segmented options={PANELS} value={panel} onChange={setPanel} />
        <span className="sc-clock" title="Tempo de simulação (pausa não conta)">⏱ {clock(data?.uptime)}</span>
        <SimControls
          controlPath="/api/scheduling/compare/control"
          status={data?.status}
          connected={connected}
        />
      </div>

      {!lanes.length ? (
        <div className="sc-empty">{connected ? "Carregando comparação…" : "Conectando ao backend…"}</div>
      ) : panel === "table" ? (
        <main className="sc-main sc-main-table">{table}</main>
      ) : (
        <>
          <MetricHighlights rows={rows} />
          <main className={`sc-main lane-grid lane-grid-${lanes.length}`}>
            {lanes.map((lane) => (
              <LaneCard key={lane.key} lane={lane} />
            ))}
            {tableInGrid && <div className="lane-grid-table">{table}</div>}
          </main>
        </>
      )}
    </>
  );
}
