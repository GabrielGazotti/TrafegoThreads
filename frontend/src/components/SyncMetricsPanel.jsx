/**
 * Helpers do modo individual: transformam os baldes de métricas
 * (`metrics.phases`, um por modo usado) em linhas para os destaques e
 * colunas para a tabela comparativa.
 */

/** Chave do balde ("priority-np+aging") -> chave de cor do modo ("priority"). */
export function laneKeyOf(bucketKey) {
  return bucketKey?.startsWith("priority") ? "priority" : bucketKey;
}

const SHORT = { off: "Semáforo OFF", fixed: "Ciclo fixo", priority: "Prioridade", fcfs: "FCFS" };

/** Todas as colunas (um balde = uma coluna), na ordem em que os modos foram usados. */
export function phaseColumns(metrics) {
  const phases = metrics?.phases;
  if (!phases) return [];
  return Object.keys(phases).map((k) => ({
    key: k,
    label: phases[k].label,
    short: SHORT[laneKeyOf(k)] ?? phases[k].label,
    stats: phases[k],
    laneKey: laneKeyOf(k),
    active: k === metrics.phase,
  }));
}

/** Destaques: Semáforo OFF x modo com semáforo (o atual, ou o último usado). */
export function highlightRows(metrics) {
  const cols = phaseColumns(metrics);
  if (!cols.length) return [];
  const off = cols.find((c) => c.key === "off");
  const current = cols.find((c) => c.active);
  const on = current && current.key !== "off" ? current : [...cols].reverse().find((c) => c.key !== "off");
  return [off, on].filter(Boolean);
}
