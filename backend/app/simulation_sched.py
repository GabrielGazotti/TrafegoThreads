"""
SimulationManagerSched — simulação da tela /scheduling.

Sempre multithread:
  * 1 Thread "spawner", 1 "monitor de colisão", 1 "reaper"
  * 1 Thread "controlador de semáforos" -> avança as fases de todos os cruzamentos
  * N Threads "veículo" (SchedVehicle)

O semáforo (ligado/desligado em tempo real por `set_sync()`) entrega cada
cruzamento a um escalonador (`scheduler.py`), trocado em tempo real por
`set_algorithm()`: ciclo fixo, Priority Scheduling (preempção / aging),
ou FCFS.
As métricas são separadas por modo: "off" ou o algoritmo em uso.

`seed` fixa o fluxo de veículos (tipos, intervalos de spawn, rotas, manobras):
duas simulações com a mesma seed recebem os mesmos veículos — é o que o modo
comparação (`simulation_compare.py`) usa para comparar algoritmos de forma justa.
"""

from __future__ import annotations

import random
import threading
import time
from collections import deque

from . import config
from .city import City
from .collisions import _in_collision_range, process_collision_clusters
from .lifecycle import Lifecycle
from .metrics_sched import SchedMetrics
from .scheduler import make_controller
from .signals import movements_conflict
from .vehicle_sched import SchedVehicle

BACKGROUND_THREADS = 4


def _in_conflict(a, b) -> bool:
    """Colisão só entre movimentos que se cruzam ou disputam a mesma saída."""
    return _in_collision_range(a, b) and movements_conflict(a.movement, b.movement)


class SimulationManagerSched(Lifecycle):
    def __init__(self, sync_enabled: bool = False, algorithm: str | None = None,
                 preemption: bool = True, aging: bool = True,
                 emergency_rate: float | None = None, seed: int | None = None) -> None:
        self.city = City(
            width=config.SCHED_CITY_WIDTH,
            height=config.SCHED_CITY_HEIGHT,
            horizontal_streets=config.SCHED_HORIZONTAL_STREETS,
            vertical_streets=config.SCHED_VERTICAL_STREETS,
        )
        self.sync_enabled = sync_enabled
        self.algorithm = algorithm if algorithm in config.SCHED_ALGORITHMS \
            else config.SCHED_DEFAULT_ALGORITHM
        self.preemption = preemption
        self.aging = aging
        # fração dos spawns que são emergência (ajustável na tela para provocar starvation)
        self.emergency_rate = config.SCHED_EMERGENCY_SPAWN_RATE if emergency_rate is None \
            else emergency_rate
        self.seed = seed if seed is not None else random.randrange(2**31)
        self.rng = random.Random(self.seed)
        self.metrics = SchedMetrics(*self._mode())
        self._install_controllers()
        self.vehicles: dict[str, SchedVehicle] = {}
        self.event_log: deque = deque(maxlen=config.EVENT_LOG_MAXLEN)
        self._init_lifecycle()

        self._threads: list[threading.Thread] = []

        types = config.SCHED_VEHICLE_TYPES
        self._emergency_types = [k for k, v in types.items()
                                 if v["priority"] >= config.PRIORITY_EMERGENCY]
        self._normal_types = [k for k in types if k not in self._emergency_types]

    def _launch(self):
        for target, name in (
            (self._spawn_loop, "sched-spawner"),
            (self._collision_monitor_loop, "sched-monitor-colisao"),
            (self._reaper_loop, "sched-reaper"),
            (self._signal_controller_loop, "sched-semaforos"),
        ):
            t = threading.Thread(target=target, name=name, daemon=True)
            t.start()
            self._threads.append(t)

        self._log_system(f"Simulação scheduling iniciada ({self._mode()[1]})")

    def _shift_time(self, dt: float) -> None:
        super()._shift_time(dt)
        for inter in self.city.intersections.values():
            with inter._lock:
                if inter.controller is not None:
                    inter.controller.shift_time(dt)

    # ------------------------------------------------------- algoritmo
    def algorithm_label(self) -> str:
        label = config.SCHED_ALGORITHMS[self.algorithm]
        if self.algorithm == "priority":
            label += " (" + ("preemptiva" if self.preemption else "não preemptiva")
            label += ", com aging)" if self.aging else ", sem aging)"
        return label

    def _mode(self) -> tuple[str, str]:
        """(chave do balde de métricas, rótulo) do modo atual."""
        if not self.sync_enabled:
            return "off", "Semáforo OFF"
        key = self.algorithm
        if self.algorithm == "priority":
            key += ("" if self.preemption else "-np") + ("+aging" if self.aging else "")
        return key, self.algorithm_label()

    def _on_controller_event(self, kind: str, message: str) -> None:
        if kind == "preempt":
            self.metrics.inc_preemptions()
        self.event_log.append(
            {"t": time.time(), "vehicle": "-", "type": "semaforo", "level": kind,
             "message": message}
        )

    def _install_controllers(self) -> None:
        """
        Controlador novo em todos os cruzamentos, com o mesmo instante de início:
        os semáforos ficam na mesma fase e quem passa no verde pega o próximo
        cruzamento do mesmo eixo também aberto ("onda verde").
        Pedidos pendentes do controlador antigo são descartados; os veículos
        parados renovam o pedido no próximo tick.
        """
        now = time.time()
        for inter in self.city.intersections.values():
            ctrl = make_controller(
                self.algorithm, now, self.preemption, self.aging,
                on_event=lambda kind, msg, iid=inter.id: self._on_controller_event(
                    kind, f"{iid}: {msg}"),
            )
            inter.set_controller(ctrl)

    def set_sync(self, enabled: bool) -> None:
        if enabled == self.sync_enabled:
            return
        self.sync_enabled = enabled
        if enabled:
            self._install_controllers()
        self.metrics.set_phase(*self._mode())
        self._log_system(f"Semáforo {'LIGADO — ' + self.algorithm_label() if enabled else 'DESLIGADO'}")

    def set_algorithm(self, algorithm: str, preemption: bool | None = None,
                      aging: bool | None = None) -> None:
        if algorithm not in config.SCHED_ALGORITHMS:
            raise ValueError(f"algoritmo desconhecido: {algorithm}")
        new = (algorithm,
               self.preemption if preemption is None else preemption,
               self.aging if aging is None else aging)
        if new == (self.algorithm, self.preemption, self.aging):
            return
        self.algorithm, self.preemption, self.aging = new
        if self.sync_enabled:
            self._install_controllers()
            self.metrics.set_phase(*self._mode())
        self._log_system(f"Escalonador: {self.algorithm_label()}")

    def set_emergency_rate(self, rate: float) -> None:
        rate = round(min(max(rate, 0.0), config.SCHED_EMERGENCY_RATE_MAX), 2)
        if rate == self.emergency_rate:
            return
        self.emergency_rate = rate
        self._log_system(f"Taxa de emergências: {rate:.0%} dos veículos gerados")

    def algorithm_state(self) -> dict:
        return {
            "name": self.algorithm,
            "label": self.algorithm_label(),
            "preemption": self.preemption,
            "aging": self.aging,
        }

    def is_sync_enabled(self) -> bool:
        return self.sync_enabled

    def _log_system(self, message: str):
        self.event_log.append(
            {"t": time.time(), "vehicle": "-", "type": "sistema", "level": "info",
             "message": message}
        )

    # ------------------------------------------------------------------
    def _pick_type(self) -> str:
        if self.rng.random() < self.emergency_rate:
            return self.rng.choice(self._emergency_types)
        return self.rng.choice(self._normal_types)

    def _spawn_loop(self):
        while self._wait_running():
            # sorteia sempre na mesma ordem, mesmo quando a cidade está cheia,
            # para a sequência continuar alinhada com as outras simulações
            vtype = self._pick_type()
            vehicle_seed = self.rng.getrandbits(32)
            interval = self.rng.uniform(config.SPAWN_INTERVAL_MIN, config.SPAWN_INTERVAL_MAX)
            if len(self.vehicles) < config.SCHED_MAX_VEHICLES:
                v = SchedVehicle(
                    self.city, self.vehicles, self.event_log, self.metrics, self.stop_flag,
                    vtype=vtype,
                    sync_enabled=self.is_sync_enabled,
                    run_gate=self.run_gate,
                    rng=random.Random(vehicle_seed),
                )
                self.vehicles[v.id] = v
                self.metrics.inc_spawned()
                v.start_as_thread()
            time.sleep(interval)

    def _signal_controller_loop(self):
        while self._wait_running():
            if self.sync_enabled:
                now = time.time()
                for inter in self.city.intersections.values():
                    inter.step_controller(now)
            time.sleep(config.SIGNAL_CONTROLLER_INTERVAL)

    def _collision_monitor_loop(self):
        while self._wait_running():
            try:
                snapshot = list(self.vehicles.values())
            except RuntimeError:
                time.sleep(config.COLLISION_CHECK_INTERVAL)
                continue

            active = [v for v in snapshot if not v.crashed and not v.finished]
            process_collision_clusters(
                active, self.city, self.metrics, self.event_log, in_range=_in_conflict
            )

            time.sleep(config.COLLISION_CHECK_INTERVAL)

    def _reaper_loop(self):
        while self._wait_running():
            now = time.time()
            for vid, v in list(self.vehicles.items()):
                if v.finished or (
                    v.crashed and v.crash_time and now - v.crash_time > config.CRASH_LINGER_TIME
                ):
                    self.vehicles.pop(vid, None)
            time.sleep(0.5)

    # ------------------------------------------------------------------
    def snapshot(self, events: bool = True) -> dict:
        vehicles_list = []
        waiting = 0
        for v in list(self.vehicles.values()):
            try:
                d = v.to_dict()
            except Exception:
                continue
            vehicles_list.append(d)
            if d["state"] == "waiting":
                waiting += 1

        intersections = self.city.snapshot()
        for inter_dict, inter in zip(intersections, self.city.intersections.values()):
            lights, info = inter.controller_snapshot()
            inter_dict["signal"] = lights
            inter_dict.update(info)

        alive = sum(1 for v in vehicles_list if not v["crashed"] and v["state"] != "finished")
        active_threads = 0 if self.status == "idle" else BACKGROUND_THREADS + alive

        return {
            "mode": "scheduling",
            "status": self.status,
            "sync_enabled": self.sync_enabled,
            "algorithm": self.algorithm_state(),
            "emergency_rate": self.emergency_rate,
            "lane_offset": config.SCHED_LANE_OFFSET,
            "vehicles": vehicles_list,
            "intersections": intersections,
            "metrics": self.metrics.snapshot(active_threads, len(vehicles_list), waiting),
            "events": list(self.event_log)[-30:] if events else [],
        }
