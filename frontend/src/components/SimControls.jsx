import React, { useState } from "react";
import { API_BASE } from "../api.js";

const PRIMARY = {
  idle: { action: "start", label: "▶ Iniciar", cls: "sim-btn-start" },
  paused: { action: "start", label: "▶ Continuar", cls: "sim-btn-start" },
  running: { action: "pause", label: "⏸ Pausar", cls: "sim-btn-pause" },
};

export default function SimControls({ controlPath, status = "idle", connected = true }) {
  const [pending, setPending] = useState(false);
  const primary = PRIMARY[status] || PRIMARY.idle;

  const send = async (action) => {
    setPending(true);
    try {
      await fetch(`${API_BASE}${controlPath}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
    } catch {

    } finally {
      setPending(false);
    }
  };

  const disabled = pending || !connected;

  return (
    <div className="sim-controls">
      <span className={`sim-status sim-status-${status}`}>{status}</span>
      <button
        type="button"
        className={`sim-btn ${primary.cls}`}
        onClick={() => send(primary.action)}
        disabled={disabled}
      >
        {primary.label}
      </button>
      <button
        type="button"
        className="sim-btn sim-btn-reset"
        onClick={() => send("reset")}
        disabled={disabled}
        title="Reiniciar"
      >
        ↺ Reiniciar
      </button>
    </div>
  );
}
