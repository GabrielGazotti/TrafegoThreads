"""
CompareManager — modo comparação da tela /scheduling.

Roda várias `SimulationManagerSched` AO MESMO TEMPO, uma por modo
("off", "fixed", "priority", "fcfs"), todas com a MESMA seed: cada uma recebe
o mesmo fluxo de veículos (tipos, horários de spawn, rotas e manobras), então
as métricas ficam comparáveis — mesmo tempo de execução, mesmo tráfego, só o
escalonador do cruzamento muda.

Cada simulação continua com suas próprias threads (veículos, spawner, monitor,
reaper, semáforos) e sua própria cidade.
"""

from __future__ import annotations

import random

from . import config
from .simulation_sched import SimulationManagerSched


class CompareManager:
    def __init__(self, lanes: list[str] | None = None, preemption: bool = True,
                 aging: bool = True, emergency_rate: float | None = None,
                 seed: int | None = None) -> None:
        self.lane_keys = self._valid_lanes(lanes or config.SCHED_COMPARE_DEFAULT)
        self.preemption = preemption
        self.aging = aging
        self.emergency_rate = config.SCHED_EMERGENCY_SPAWN_RATE if emergency_rate is None \
            else emergency_rate
        self.seed = seed if seed is not None else random.randrange(2**31)
        self.lanes = [self._make_lane(k) for k in self.lane_keys]

    @staticmethod
    def _valid_lanes(lanes: list[str]) -> list[str]:
        # mantém a ordem canônica e remove duplicados / chaves desconhecidas
        chosen = [k for k in config.SCHED_COMPARE_LANES if k in set(lanes)]
        if len(chosen) < 2:
            raise ValueError("escolha pelo menos 2 modos para comparar")
        return chosen

    def _make_lane(self, key: str) -> SimulationManagerSched:
        return SimulationManagerSched(
            sync_enabled=key != "off",
            algorithm=None if key == "off" else key,
            preemption=self.preemption,
            aging=self.aging,
            emergency_rate=self.emergency_rate,
            seed=self.seed,
        )

    # ---------------------------------------------------------- ciclo de vida
    @property
    def status(self) -> str:
        return self.lanes[0].status

    def start(self) -> None:
        for lane in self.lanes:
            lane.start()

    def pause(self) -> None:
        for lane in self.lanes:
            lane.pause()

    def stop(self) -> None:
        for lane in self.lanes:
            lane.stop()

    def rebuilt(self, lanes: list[str] | None = None, preemption: bool | None = None,
                aging: bool | None = None, new_seed: bool = True) -> "CompareManager":
        """Encerra esta comparação e devolve uma nova (mesmo status: rodando continua rodando)."""
        was_running = self.status == "running"
        new = CompareManager(
            lanes=self.lane_keys if lanes is None else lanes,
            preemption=self.preemption if preemption is None else preemption,
            aging=self.aging if aging is None else aging,
            emergency_rate=self.emergency_rate,
            seed=None if new_seed else self.seed,
        )
        self.stop()
        if was_running:
            new.start()
        return new

    def set_emergency_rate(self, rate: float) -> None:
        for lane in self.lanes:
            lane.set_emergency_rate(rate)
        self.emergency_rate = self.lanes[0].emergency_rate

    # ---------------------------------------------------------------- estado
    def snapshot(self) -> dict:
        lanes = []
        for key, lane in zip(self.lane_keys, self.lanes):
            snap = lane.snapshot(events=False)
            m = snap["metrics"]
            snap["key"] = key
            snap["label"] = "Semáforo OFF" if key == "off" else lane.algorithm_label()
            snap["stats"] = m["phases"][m["phase"]]
            lanes.append(snap)
        return {
            "mode": "scheduling-compare",
            "status": self.status,
            "seed": self.seed,
            "lane_keys": self.lane_keys,
            "available_lanes": config.SCHED_COMPARE_LANES,
            "preemption": self.preemption,
            "aging": self.aging,
            "emergency_rate": self.emergency_rate,
            "uptime": lanes[0]["metrics"]["uptime"] if lanes else 0,
            "lanes": lanes,
        }
