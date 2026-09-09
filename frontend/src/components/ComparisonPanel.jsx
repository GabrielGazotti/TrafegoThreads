import React from "react";

const ROWS = [
  { key: "uptime", label: "Tempo total (s)", get: (m) => m?.uptime ?? 0 },
  { key: "collisions", label: "Colisões", get: (m) => m?.collisions ?? 0 },
  {
    key: "intersection_conflicts",
    label: "Conflitos de corrida (race)",
    get: (m) => m?.intersection_conflicts ?? 0,
  },
  { key: "vehicles_involved", label: "Veículos envolvidos", get: (m) => m?.vehicles_involved ?? 0 },
];

function winnerClass(multiVal, monoVal) {
  if (multiVal === monoVal) return { multi: "", mono: "" };
  return multiVal < monoVal
    ? { multi: "cmp-better", mono: "cmp-worse" }
    : { multi: "cmp-worse", mono: "cmp-better" };
}

export default function ComparisonPanel({ multiData, monoData }) {
  const multiMetrics = multiData?.metrics;
  const monoMetrics = monoData?.metrics;

  if (!multiMetrics || !monoMetrics) return null;

  return (
    <div className="comparison-panel">
      <div className="comparison-title">Comparativo MULTI vs MONO</div>
      <table className="comparison-table">
        <thead>
          <tr>
            <th>Métrica</th>
            <th className="cmp-col-multi">MULTI</th>
            <th className="cmp-col-mono">MONO</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => {
            const multiVal = row.get(multiMetrics);
            const monoVal = row.get(monoMetrics);
            const cls = winnerClass(multiVal, monoVal);
            return (
              <tr key={row.key}>
                <td className="cmp-label">{row.label}</td>
                <td className={`cmp-val ${cls.multi}`}>{multiVal}</td>
                <td className={`cmp-val ${cls.mono}`}>{monoVal}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}