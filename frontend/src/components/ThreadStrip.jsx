import React from "react";

const STATE_CLASS = {
  moving: "thread-moving",
  crossing: "thread-crossing",
  waiting: "thread-waiting",
  crashed: "thread-crashed",
  finished: "thread-finished",
};

function VehicleToken({ vehicle, mode, tickingId }) {
  const isMono = mode === "mono";
  const isTicking = isMono && tickingId === vehicle.id;
  const isMultiActive = !isMono;

  return (
    <span
      className={[
        "vehicle-token",
        STATE_CLASS[vehicle.state] || "thread-moving",
        isMono ? "vehicle-token-mono" : "vehicle-token-multi",
        isTicking ? "mono-ticking" : "",
        isMultiActive ? "multi-active" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      title={vehicle.id}
    >
      {isTicking && <span className="mono-tick-arrow">▶</span>}
      {vehicle.emoji}
    </span>
  );
}

export default function ThreadStrip({ mode, vehicles = [], activeThreads = 0, peakThreads = 0, tickingId = null }) {
  const active = vehicles.filter((v) => !v.crashed && v.state !== "finished");
  const isMono = mode === "mono";

  return (
    <div className={`thread-strip thread-strip-${mode}`}>
      <div className={`thread-count ${isMono ? "mono-count" : "multi-count"}`}>
        {isMono ? 1 : activeThreads}
        <span className="thread-peak" title="Pico de Threads simultâneas">
          pico {isMono ? 1 : peakThreads}
        </span>
      </div>
      <div className="vehicle-strip-wrap">
        <span className={`thread-strip-caption ${isMono ? "mono-caption" : "multi-caption"}`}>
          {isMono ? "1 por vez" : `${active.length} paralelos`}
        </span>
        <div className="vehicle-token-row">
          {active.map((v) => (
            <VehicleToken key={v.id} vehicle={v} mode={mode} tickingId={tickingId} />
          ))}
        </div>
      </div>
    </div>
  );
}
