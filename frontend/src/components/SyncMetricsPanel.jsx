import React from "react";
import { MetricBar } from "./UtilizationPanel.jsx";

const BAR_METRICS = [
  { key: "collisions", label: "Colisões", hint: "total" },
  { key: "intersection_conflicts", label: "Race", hint: "janela" },
  { key: "average_wait_time", label: "Espera", hint: "média (s)" },
  { key: "average_trip_time", label: "Viagem", hint: "média (s)" },
];

const ROWS = [
  { key: "collisions", label: "Colisões" },
  { key: "intersection_conflicts", label: "Race conditions" },
  { key: "average_wait_time", label: "Espera média (s)", decimals: 2, average: true },
  { key: "average_trip_time", label: "Viagem média (s)", decimals: 2, average: true },
];

const PHASES = [
  { key: "off", label: "Semáforo OFF" },
  { key: "on", label: "Semáforo ON" },
];

function format(value, decimals) {
  if (typeof value !== "number") return "—";
  return decimals ? value.toFixed(decimals) : value;
}

function winnerClass(row, offVal, onVal) {
  if (offVal === onVal) return { off: "", on: "" };
  // média 0 = fase ainda sem amostras, não significa "melhor"
  if (row.average && (offVal === 0 || onVal === 0)) return { off: "", on: "" };
  return offVal < onVal
    ? { off: "cmp-better", on: "cmp-worse" }
    : { off: "cmp-worse", on: "cmp-better" };
}

export default function SyncMetricsPanel({ metrics }) {
  const phases = metrics?.phases;
  if (!phases) return null;

  const { off, on } = phases;
  const scales = Object.fromEntries(
    BAR_METRICS.map((m) => [m.key, Math.max(off[m.key] ?? 0, on[m.key] ?? 0, 1)])
  );

  return (
    <>
      <div className="compare-bars utilization-panel">
        {PHASES.map((phase) => (
          <div key={phase.key} className={`compare-panel compare-panel-${phase.key}`}>
            <span className={`compare-panel-title ${phase.key}-title`}>{phase.label}</span>
            <div className="util-metrics-row">
              {BAR_METRICS.map((m) => (
                <MetricBar
                  key={m.key}
                  label={m.label}
                  hint={m.hint}
                  value={phases[phase.key][m.key] ?? 0}
                  mode={phase.key}
                  max={scales[m.key]}
                />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="comparison-panel">
        <div className="comparison-title">Comparativo OFF vs ON</div>
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Métrica</th>
              <th className="cmp-col-off">OFF</th>
              <th className="cmp-col-on">ON</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => {
              const offVal = off[row.key];
              const onVal = on[row.key];
              const cls = winnerClass(row, offVal, onVal);
              return (
                <tr key={row.key}>
                  <td className="cmp-label">{row.label}</td>
                  <td className={`cmp-val ${cls.off}`}>{format(offVal, row.decimals)}</td>
                  <td className={`cmp-val ${cls.on}`}>{format(onVal, row.decimals)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
