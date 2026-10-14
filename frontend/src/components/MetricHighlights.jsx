import React from "react";
import { formatMetric } from "./ModeComparisonTable.jsx";

// o que a apresentação precisa mostrar de relance
export const HIGHLIGHTS = [
  { key: "collisions", label: "Colisões", hint: "menor é melhor", better: "low" },
  { key: "average_wait_time_emergency", label: "Espera 🚑 emergência", hint: "média (s)", better: "low", decimals: 1 },
  { key: "average_wait_time_normal", label: "Espera 🚗 comum", hint: "média (s)", better: "low", decimals: 1 },
  { key: "max_wait_time_normal", label: "Espera máx. 🚗", hint: "starvation (s)", better: "low", decimals: 1 },
  { key: "throughput_per_min", label: "Vazão", hint: "veíc/min · maior é melhor", better: "high", decimals: 1 },
];

/** Índices dos melhores valores (empates incluídos); vazio se todos iguais ou sem dados. */
function bestIndexes(values, better) {
  const valid = values.map((v, i) => ({ v, i })).filter(({ v }) => typeof v === "number");
  if (valid.length < 2) return new Set();
  const nums = valid.map((x) => x.v);
  const target = better === "low" ? Math.min(...nums) : Math.max(...nums);
  if (nums.every((v) => v === target)) return new Set();
  return new Set(valid.filter(({ v }) => v === target).map(({ i }) => i));
}

function HighlightCard({ metric, rows }) {
  const values = rows.map((r) => r.stats?.[metric.key]);
  const max = Math.max(...values.map((v) => (typeof v === "number" ? v : 0)), 0.0001);
  const best = bestIndexes(values, metric.better);
  return (
    <div className="hl-card">
      <div className="hl-head">
        <span className="hl-label">{metric.label}</span>
        <span className="hl-hint">{metric.hint}</span>
      </div>
      {rows.map((row, i) => {
        const v = values[i];
        const pct = typeof v === "number" ? Math.max((v / max) * 100, v > 0 ? 3 : 0) : 0;
        return (
          <div key={row.key} className={`hl-row lane-${row.laneKey} ${best.has(i) ? "hl-best" : ""}`}>
            <span className="hl-lane" title={row.label}>{row.short ?? row.label}</span>
            <span className="hl-track">
              <span className="hl-fill" style={{ width: `${pct}%` }} />
            </span>
            <span className="hl-val">
              {formatMetric(v, metric.decimals)}
              <span className="hl-star">{best.has(i) ? "★" : ""}</span>
            </span>
          </div>
        );
      })}
    </div>
  );
}

/** rows: [{ key, label, short?, laneKey, stats }] — uma barra por modo em cada métrica. */
export default function MetricHighlights({ rows, metrics = HIGHLIGHTS }) {
  if (!rows?.length) return null;
  return (
    <div className="hl-grid">
      {metrics.map((m) => (
        <HighlightCard key={m.key} metric={m} rows={rows} />
      ))}
    </div>
  );
}
