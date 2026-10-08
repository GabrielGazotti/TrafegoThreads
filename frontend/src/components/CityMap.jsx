import React, { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:8000`;

const DEFAULT_ROAD_WIDTH = 26;
const SIGNAL_W = 38;
const SIGNAL_H = 14;

// mão direita: o sinal fica à direita de quem chega, recuado para dentro da rua
function signalOffsets(road, radius) {
  const dist = radius + 30;
  const sideH = road / 2 + SIGNAL_H / 2 + 3;
  const sideV = road / 2 + SIGNAL_W / 2 + 3;
  return {
    W: { dx: -dist, dy: sideH },
    E: { dx: dist, dy: -sideH },
    N: { dx: -sideV, dy: -dist },
    S: { dx: sideV, dy: dist },
  };
}

const APPROACH_HEADING = { W: [1, 0], E: [-1, 0], N: [0, 1], S: [0, -1] };

const leftOf = ([dx, dy]) => [dy, -dx];
const rightOf = ([dx, dy]) => [-dy, dx];

function lampClass(signals, inter, approach, maneuver) {
  if (signals !== "on" || !inter.signal) return "signal-off";
  return `signal-${inter.signal[approach][maneuver]}`;
}

function arrowPoints(cx, [ux, uy]) {
  const [px, py] = [-uy, ux];
  const tip = [cx + ux * 4, uy * 4];
  const b1 = [cx - ux * 3 + px * 3.5, -uy * 3 + py * 3.5];
  const b2 = [cx - ux * 3 - px * 3.5, -uy * 3 - py * 3.5];
  return [tip, b1, b2].map((p) => p.join(",")).join(" ");
}

// cada lado de chegada tem 3 luzes: seta esquerda, reto (círculo) e seta direita
function IntersectionSignals({ inter, signals, offsets }) {
  return Object.entries(offsets).map(([approach, { dx, dy }]) => {
    const heading = APPROACH_HEADING[approach];
    return (
      <g key={approach} transform={`translate(${inter.x + dx}, ${inter.y + dy})`}>
        <rect
          x={-SIGNAL_W / 2}
          y={-SIGNAL_H / 2}
          width={SIGNAL_W}
          height={SIGNAL_H}
          rx={3}
          className="signal-housing"
        />
        <polygon
          points={arrowPoints(-12, leftOf(heading))}
          className={`signal-light ${lampClass(signals, inter, approach, "left")}`}
        />
        <circle r={4.5} className={`signal-light ${lampClass(signals, inter, approach, "straight")}`} />
        <polygon
          points={arrowPoints(12, rightOf(heading))}
          className={`signal-light ${lampClass(signals, inter, approach, "right")}`}
        />
      </g>
    );
  });
}

// tracejado que separa a faixa de conversão à esquerda nos metros finais antes do cruzamento
function LeftPocketLines({ inter, cfg }) {
  const r = cfg.intersection_radius;
  const p = cfg.left_pocket;
  const b = (cfg.lane_offset + cfg.left_lane_offset) / 2;
  const { x, y } = inter;
  const segs = [
    [x - r - p, y + b, x - r, y + b],
    [x + r, y - b, x + r + p, y - b],
    [x - b, y - r - p, x - b, y - r],
    [x + b, y + r, x + b, y + r + p],
  ];
  return segs.map(([x1, y1, x2, y2], i) => (
    <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} className="pocket-divider" />
  ));
}

function vehicleRotation(axis, direction) {
  if (axis === "H") return direction === 1 ? "rotate(0deg)" : "scaleX(-1)";
  return direction === 1 ? "rotate(90deg)" : "rotate(-90deg)";
}

function Blinker({ vehicle }) {
  if (vehicle.crashed || !["left", "right"].includes(vehicle.maneuver)) return null;
  const heading = vehicle.axis === "H" ? [vehicle.direction, 0] : [0, vehicle.direction];
  const [sx, sy] = vehicle.maneuver === "left" ? leftOf(heading) : rightOf(heading);
  return (
    <circle
      cx={sx * 7 + heading[0] * 5}
      cy={sy * 7 + heading[1] * 5}
      r={2.5}
      className="blinker"
    />
  );
}

export default function CityMap({
  vehicles = [],
  intersections = [],
  signals = null,
  lanes = false,
  configPath = "/api/config",
}) {
  const [cityConfig, setCityConfig] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}${configPath}`)
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
  }, [configPath]);

  if (!cityConfig) {
    return <div className="city-map-loading">Carregando mapa da cidade…</div>;
  }

  const { city_width: W, city_height: H, horizontal_streets: hs, vertical_streets: vs } = cityConfig;
  const ROAD_WIDTH = cityConfig.road_width ?? DEFAULT_ROAD_WIDTH;
  const offsets = signalOffsets(ROAD_WIDTH, cityConfig.intersection_radius ?? 22);
  const hasPockets = lanes && cityConfig.left_pocket != null;

  return (
    <svg
      className="city-map"
      viewBox={`0 0 ${W} ${H}`}
      width="100%"
      height="100%"
      style={{ aspectRatio: `${W} / ${H}` }}
    >
      <rect x={0} y={0} width={W} height={H} className="city-bg" />

      {hs.map((y, i) => (
        <rect key={`h-${i}`} x={0} y={y - ROAD_WIDTH / 2} width={W} height={ROAD_WIDTH} className="road" />
      ))}
      {vs.map((x, i) => (
        <rect key={`v-${i}`} x={x - ROAD_WIDTH / 2} y={0} width={ROAD_WIDTH} height={H} className="road" />
      ))}
      {lanes && hs.map((y, i) => (
        <line key={`hl-${i}`} x1={0} y1={y} x2={W} y2={y} className="lane-divider" />
      ))}
      {lanes && vs.map((x, i) => (
        <line key={`vl-${i}`} x1={x} y1={0} x2={x} y2={H} className="lane-divider" />
      ))}

      {intersections.map((inter) => {
        const conflict = !lanes && inter.occupants && inter.occupants.length > 1;
        return (
          <g key={inter.id}>
            {conflict && (
              <circle cx={inter.x} cy={inter.y} r={ROAD_WIDTH} className="conflict-ring" />
            )}
            <circle cx={inter.x} cy={inter.y} r={ROAD_WIDTH / 2 + 2} className="intersection-base" />
            {hasPockets && <LeftPocketLines inter={inter} cfg={cityConfig} />}
            {signals && <IntersectionSignals inter={inter} signals={signals} offsets={offsets} />}
            {!lanes && inter.occupants && inter.occupants.length > 0 && (
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
            fontSize={lanes ? (v.crashed ? 16 : 14) : v.crashed ? 22 : 20}
            className={`vehicle ${v.state} ${v.crashed ? "crashed" : ""} ${v.emergency ? "emergency" : ""}`}
            transform={vehicleRotation(v.axis, v.direction)}
            style={{ opacity: v.crashed ? 0.55 : 1 }}
          >
            {v.emoji}
          </text>
          {lanes && <Blinker vehicle={v} />}
          {v.crashed && (
            <text x={0} y={-14} textAnchor="middle" fontSize={18} className="crash-boom">
              💥
            </text>
          )}
          {!lanes && v.state === "waiting" && !v.crashed && (
            <text x={0} y={-16} textAnchor="middle" fontSize={12} className="wait-badge">
              ⏳
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}
