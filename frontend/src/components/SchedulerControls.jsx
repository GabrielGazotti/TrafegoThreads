import React, { useEffect, useRef, useState } from "react";
import { API_BASE } from "../api.js";

export const ALGORITHMS = [
  { key: "fixed", label: "Ciclo fixo", title: "6 fases sempre na mesma ordem (Priority Scheduling desligado)" },
  { key: "priority", label: "Prioridade", title: "Fila de prioridade (heapq): emergência primeiro" },
  { key: "fcfs", label: "FCFS", title: "First Come, First Served — abre a fase de quem chegou primeiro" },
];

export async function post(path, body) {
  try {
    await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    // o próximo frame do WebSocket mostra o estado real
  }
}

export function Toggle({ label, title, on, disabled, onClick }) {
  return (
    <button
      type="button"
      className={`sc-toggle ${on ? "sc-toggle-on" : ""}`}
      onClick={onClick}
      disabled={disabled}
      title={title}
      aria-pressed={on}
    >
      <span className="sc-toggle-dot" />
      {label} {on ? "ON" : "OFF"}
    </button>
  );
}

/** Botões lado a lado; `options` = [{ key, label, title? }]. */
export function Segmented({ options, value, onChange, disabled, className = "", title }) {
  return (
    <div className={`sc-seg ${disabled ? "sc-seg-disabled" : ""} ${className}`} title={title}>
      {options.map((o) => (
        <button
          key={o.key}
          type="button"
          className={value === o.key ? "sc-seg-active" : ""}
          onClick={() => onChange(o.key)}
          disabled={disabled || value === o.key}
          title={o.title}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** Slider da fração de emergências; envia só quando o usuário para de arrastar. */
export function EmergencyRateSlider({ value = 0.15, max = 0.8, disabled, onCommit }) {
  const [draft, setDraft] = useState(null);
  const timer = useRef(null);

  useEffect(() => {
    if (draft === null) return undefined;
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      await onCommit(draft / 100);
      setDraft(null);
    }, 250);
    return () => clearTimeout(timer.current);
  }, [draft, onCommit]);

  const pct = draft ?? Math.round(value * 100);
  return (
    <label className="sc-group sc-rate" title="Fração dos veículos gerados que são de emergência">
      <span className="sc-label">🚑</span>
      <input
        type="range"
        min={0}
        max={Math.round(max * 100)}
        step={5}
        value={pct}
        onChange={(e) => setDraft(Number(e.target.value))}
        disabled={disabled}
      />
      <span className="sc-rate-val">{pct}%</span>
    </label>
  );
}

const commitRate = (rate) => post("/api/scheduling/emergency-rate", { rate });

/** Grupos de controle do escalonador (modo individual), para colocar dentro da barra. */
export default function SchedulerControls({ algorithm, syncEnabled, emergencyRate = 0.15, connected }) {
  const [pending, setPending] = useState(false);

  const name = algorithm?.name ?? "fixed";
  const preemption = algorithm?.preemption ?? true;
  const aging = algorithm?.aging ?? true;
  const locked = !syncEnabled || !connected || pending;

  const choose = async (body) => {
    setPending(true);
    await post("/api/scheduling/algorithm", { algorithm: name, ...body });
    setPending(false);
  };

  return (
    <>
      <Segmented
        options={ALGORITHMS}
        value={name}
        onChange={(key) => choose({ algorithm: key })}
        disabled={locked}
        title={!syncEnabled ? "Ligue o semáforo para escolher o algoritmo" : "Escalonador do cruzamento"}
      />
      {name === "priority" && (
        <div className="sc-group">
          <Toggle
            label="Preempção"
            title="Emergência parada no vermelho corta o verde atual e abre a sua fase"
            on={preemption}
            disabled={locked}
            onClick={() => choose({ preemption: !preemption })}
          />
          <Toggle
            label="Aging"
            title="Prioridade efetiva sobe com o tempo de espera (evita starvation)"
            on={aging}
            disabled={locked}
            onClick={() => choose({ aging: !aging })}
          />
        </div>
      )}
      <EmergencyRateSlider value={emergencyRate} disabled={!connected} onCommit={commitRate} />
    </>
  );
}
