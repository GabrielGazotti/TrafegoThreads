import React, { useEffect, useRef } from "react";

const LEVEL_LABEL = {
  info: "ℹ️",
  wait: "🟡",
  warn: "🚨",
  race: "⚠️",
  crash: "💥",
};

export default function EventLog({ events = [] }) {
  const boxRef = useRef(null);

  useEffect(() => {
    if (boxRef.current) {
      boxRef.current.scrollTop = boxRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="event-log" ref={boxRef}>
      {events.map((e, i) => (
        <div key={i} className={`event-line event-${e.level}`}>
          <span className="event-icon">{LEVEL_LABEL[e.level] || "•"}</span>
          <span className="event-vehicle">[{e.vehicle}]</span>
          <span className="event-message">{e.message}</span>
        </div>
      ))}
      {events.length === 0 && <div className="event-line">Aguardando eventos…</div>}
    </div>
  );
}
