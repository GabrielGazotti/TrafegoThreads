import React from "react";

export default function Legend() {
  return (
    <div className="legend">
      <div>⏳ Veículo hesitando/aguardando</div>
      <div>💥 Colisão / veículo destruído</div>
      <div>🔴 Anel pulsante = disputa simultânea pelo cruzamento (race condition)</div>
    </div>
  );
}
