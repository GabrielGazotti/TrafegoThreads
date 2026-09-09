import React from "react";

const BAR_METRICS = [
  {
    key: "threads",
    label: "Threads",
    hint: "paralelo",
    hintMono: "fila",
    getValue: (data) => data?.metrics?.active_threads ?? 0,
  },
  {
    key: "ticks",
    label: "Vel. Média",
    hint: "ritmo",
    hintMono: "ritmo",
    getValue: (data) => data?.utilization?.ticks_per_second ?? data?.metrics?.ticks_per_second ?? 0,
  },
  {
    key: "race",
    label: "Race",
    hint: "janela",
    hintMono: "janela",
    getValue: (data) => data?.metrics?.intersection_conflicts ?? 0,
  },
  {
    key: "vehicles_involved",
    label: "Veíc. env.",
    hint: "total",
    hintMono: "total",
    getValue: (data) => data?.metrics?.vehicles_involved ?? 0,
  },
];

function MetricBar({ label, hint, value, mode, max }) {
  const pct = (value / max) * 100;
  const display =
    typeof value === "number" && !Number.isInteger(value) ? value.toFixed(1) : value;

  return (
    <div className="util-metric-row">
      <div className="util-metric-labels">
        <span className="util-label">{label}</span>
        <span className="util-hint">{hint}</span>
      </div>
      <div className={`compare-bar-side ${mode}-side`}>
        <div className={`compare-bar-fill ${mode}-fill`} style={{ width: `${pct}%` }} />
        <span className="compare-val">{display}</span>
      </div>
    </div>
  );
}

export default function UtilizationPanel({ multiData, monoData }) {
  if (!multiData?.metrics || !monoData?.metrics) return null;

  const barScales = Object.fromEntries(
    BAR_METRICS.map((m) => [
      m.key,
      Math.max(m.getValue(multiData), m.getValue(monoData), 1),
    ])
  );

  return (
    <div className="compare-bars utilization-panel">
      <div className="compare-panel compare-panel-multi">
        <span className="compare-panel-title multi-title">MULTI</span>
        <div className="util-metrics-row">
          {BAR_METRICS.map((m) => (
            <MetricBar
              key={m.key}
              label={m.label}
              hint={m.hint}
              value={m.getValue(multiData)}
              mode="multi"
              max={barScales[m.key]}
            />
          ))}
        </div>
      </div>
      <div className="compare-panel compare-panel-mono">
        <span className="compare-panel-title mono-title">MONO</span>
        <div className="util-metrics-row">
          {BAR_METRICS.map((m) => (
            <MetricBar
              key={m.key}
              label={m.label}
              hint={m.hintMono}
              value={m.getValue(monoData)}
              mode="mono"
              max={barScales[m.key]}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
