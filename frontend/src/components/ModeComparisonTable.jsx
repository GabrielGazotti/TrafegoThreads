import React from "react";

// better: "low" = menor é melhor, "high" = maior é melhor, null = sem destaque.
export const COMPARISON_ROWS = [
  { key: "collisions", label: "Colisões", better: "low" },
  { key: "intersection_conflicts", label: "Race conditions", better: "low" },
  { key: "throughput_per_min", label: "Vazão (veíc/min)", decimals: 1, better: "high" },
  { key: "average_wait_time", label: "Espera média (s)", decimals: 2, better: "low" },
  { key: "average_wait_time_emergency", label: "Espera média — 🚑 emergência", decimals: 2, better: "low" },
  { key: "average_wait_time_normal", label: "Espera média — 🚗 comum", decimals: 2, better: "low" },
  { key: "max_wait_time_emergency", label: "Espera máx. — 🚑 emergência", decimals: 1, better: "low" },
  { key: "max_wait_time_normal", label: "Espera máx. — 🚗 comum (starvation)", decimals: 1, better: "low" },
  { key: "average_trip_time_emergency", label: "Viagem média — 🚑 emergência", decimals: 2, better: "low" },
  { key: "average_trip_time_normal", label: "Viagem média — 🚗 comum", decimals: 2, better: "low" },
  { key: "vehicles_finished", label: "Veículos finalizados", better: "high" },
  { key: "preemptions", label: "Preempções do semáforo", better: null },
  { key: "elapsed", label: "Tempo no modo (s)", decimals: 0, better: null },
];

export function formatMetric(value, decimals) {
  if (typeof value !== "number") return "—";
  return decimals !== undefined ? value.toFixed(decimals) : String(value);
}

/** Classe de cada coluna na linha: melhor em verde, pior em vermelho. null = sem dados. */
export function rowClasses(better, values) {
  const cls = values.map(() => "");
  if (!better) return cls;
  const valid = values.map((v, i) => ({ v, i })).filter(({ v }) => typeof v === "number");
  if (valid.length < 2) return cls;
  const nums = valid.map(({ v }) => v);
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  if (min === max) return cls;
  const best = better === "low" ? min : max;
  const worst = better === "low" ? max : min;
  valid.forEach(({ v, i }) => {
    if (v === best) cls[i] = "cmp-better";
    else if (v === worst) cls[i] = "cmp-worse";
  });
  return cls;
}

/**
 * columns: [{ key, label, stats, laneKey?, active? }]
 * `laneKey` pinta o cabeçalho com a cor do modo; `active` destaca a coluna.
 */
export default function ModeComparisonTable({ title = "Comparativo por modo", columns, rows = COMPARISON_ROWS }) {
  if (!columns?.length) return null;
  return (
    <div className="comparison-panel">
      <div className="comparison-title">{title}</div>
      <div className="comparison-scroll">
        <table className="comparison-table sched-table">
          <thead>
            <tr>
              <th>Métrica</th>
              {columns.map((c) => (
                <th
                  key={c.key}
                  className={`lane-th lane-${c.laneKey ?? "on"} ${c.active ? "cmp-col-active" : ""}`}
                >
                  {c.label}
                  {c.active && " ●"}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const values = columns.map((c) => c.stats?.[row.key]);
              const cls = rowClasses(row.better, values);
              return (
                <tr key={row.key}>
                  <td className="cmp-label" title={row.label}>{row.label}</td>
                  {columns.map((c, i) => (
                    <td key={c.key} className={`cmp-val ${cls[i]} ${c.active ? "cmp-col-active" : ""}`}>
                      {formatMetric(values[i], row.decimals)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
