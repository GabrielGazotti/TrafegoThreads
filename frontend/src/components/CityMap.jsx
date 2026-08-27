import React, { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;

const ROAD_WIDTH = 26;

function vehicleRotation(axis, direction) {
  if (axis === "H") return direction === 1 ? "rotate(0deg)" : "scaleX(-1)";
  return direction === 1 ? "rotate(90deg)" : "rotate(-90deg)";
}

export default function CityMap({ vehicles = [], intersections = [] }) {
  const [cityConfig, setCityConfig] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/config`)
      .then((r) => r.json())
      .then(setCityConfig)
      .catch(() => {
        setCityConfig({
          city_width: 900,
          city_height: 650,
          horizontal_streets: [100, 250, 400, 550],
          vertical_streets: [120, 320, 520, 720],
        });
      });
  }, []);

  if (!cityConfig) {
    return <div className="city-map-loading">Carregando mapa da cidade…</div>;
  }

  const { city_width: W, city_height: H, horizontal_streets: hs, vertical_streets: vs } = cityConfig;

  return (
    <svg className="city-map" viewBox={`0 0 ${W} ${H}`} width="100%" height="100%">
      <rect x={0} y={0} width={W} height={H} className="city-bg" />

      {hs.map((y, i) => (
        <rect key={`h-${i}`} x={0} y={y - ROAD_WIDTH / 2} width={W} height={ROAD_WIDTH} className="road" />
      ))}
      {vs.map((x, i) => (
        <rect key={`v-${i}`} x={x - ROAD_WIDTH / 2} y={0} width={ROAD_WIDTH} height={H} className="road" />
      ))}

      {intersections.map((inter) => {
        const conflict = inter.occupants && inter.occupants.length > 1;
        return (
          <g key={inter.id}>
            {conflict && (
              <circle cx={inter.x} cy={inter.y} r={ROAD_WIDTH} className="conflict-ring" />
            )}
            <circle cx={inter.x} cy={inter.y} r={ROAD_WIDTH / 2 + 2} className="intersection-base" />
            {inter.occupants && inter.occupants.length > 0 && (
              <text x={inter.x} y={inter.y + 3} textAnchor="middle" className="occupant-count">
                {inter.occupants.length > 1 ? inter.occupants.length : ""}
              </text>
            )}
          </g>
        );
      })}
      {vehicles.map((v) => (
        <g key={v.id} transform={`translate(${v.x}, ${v.y})`}>
          <text
            x={0}
            y={0}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={v.crashed ? 22 : 20}
            className={`vehicle ${v.state} ${v.crashed ? "crashed" : ""}`}
            transform={vehicleRotation(v.axis, v.direction)}
            style={{ opacity: v.crashed ? 0.55 : 1 }}
          >
            {v.emoji}
          </text>
          {v.crashed && (
            <text x={0} y={-14} textAnchor="middle" fontSize={18} className="crash-boom">
              💥
            </text>
          )}
          {v.state === "waiting" && !v.crashed && (
            <text x={0} y={-16} textAnchor="middle" fontSize={12} className="wait-badge">
              ⏳
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}
