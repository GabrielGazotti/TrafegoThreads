"""
SimulationManagerSched — simulação da tela /scheduling.

Sempre multithread:
  * 1 Thread "spawner", 1 "monitor de colisão", 1 "reaper"
  * 1 Thread "controlador de semáforos" -> avança as fases de todos os cruzamentos
  * N Threads "veículo" (SchedVehicle)

O semáforo (ligado/desligado em tempo real por `set_sync()`) funciona como
um cruzamento real: N/S reto+direita, N/S esquerda, L/O reto+direita,
L/O esquerda, com amarelo e vermelho geral entre as fases.
As métricas são separadas pela fase (ON / OFF).
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
from .signals import TrafficSignal, movements_conflict
from .vehicle_sched import SchedVehicle

BACKGROUND_THREADS = 4


def _in_conflict(a, b) -> bool:
    """Colisão só entre movimentos que se cruzam ou disputam a mesma saída."""
    return _in_collision_range(a, b) and movements_conflict(a.movement, b.movement)


class SimulationManagerSched(Lifecycle):
    def __init__(self, sync_enabled: bool = False) -> None:
        self.city = City(
            width=config.SCHED_CITY_WIDTH,
            height=config.SCHED_CITY_HEIGHT,
            horizontal_streets=config.SCHED_HORIZONTAL_STREETS,
            vertical_streets=config.SCHED_VERTICAL_STREETS,
        )
        # todos os semáforos na mesma fase: quem passa no verde pega o próximo
        # cruzamento do mesmo eixo também aberto ("onda verde")
        now = time.time()
        for inter in self.city.intersections.values():
            inter.signal = TrafficSignal(start_phase=0, now=now)

        self.sync_enabled = sync_enabled
        self.metrics = SchedMetrics(sync_enabled)
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

        self._log_system(
            f"Simulação scheduling iniciada (semáforo {'ON' if self.sync_enabled else 'OFF'})"
        )

    def _shift_time(self, dt: float) -> None:
        super()._shift_time(dt)
        for inter in self.city.intersections.values():
            with inter._lock:
                inter.signal.stage_end += dt

    def set_sync(self, enabled: bool) -> None:
        if enabled == self.sync_enabled:
            return
        self.sync_enabled = enabled
        self.metrics.set_phase(enabled)
        self._log_system(f"Semáforo {'LIGADO' if enabled else 'DESLIGADO'}")

    def is_sync_enabled(self) -> bool:
        return self.sync_enabled

    def _log_system(self, message: str):
        self.event_log.append(
            {"t": time.time(), "vehicle": "-", "type": "sistema", "level": "info",
             "message": message}
        )

    # ------------------------------------------------------------------
    def _pick_type(self) -> str:
        if random.random() < config.SCHED_EMERGENCY_SPAWN_RATE:
            return random.choice(self._emergency_types)
        return random.choice(self._normal_types)

    def _spawn_loop(self):
        while self._wait_running():
            if len(self.vehicles) < config.SCHED_MAX_VEHICLES:
                v = SchedVehicle(
                    self.city, self.vehicles, self.event_log, self.metrics, self.stop_flag,
                    vtype=self._pick_type(),
                    sync_enabled=self.is_sync_enabled,
                    run_gate=self.run_gate,
                )
                self.vehicles[v.id] = v
                self.metrics.inc_spawned()
                v.start_as_thread()
            time.sleep(random.uniform(config.SPAWN_INTERVAL_MIN, config.SPAWN_INTERVAL_MAX))

    def _signal_controller_loop(self):
        while self._wait_running():
            now = time.time()
            for inter in self.city.intersections.values():
                inter.step_signal(now)
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
    def snapshot(self) -> dict:
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
            inter_dict["signal"] = inter.signal.state() if inter.signal else None

        alive = sum(1 for v in vehicles_list if not v["crashed"] and v["state"] != "finished")
        active_threads = 0 if self.status == "idle" else BACKGROUND_THREADS + alive

        return {
            "mode": "scheduling",
            "status": self.status,
            "sync_enabled": self.sync_enabled,
            "lane_offset": config.SCHED_LANE_OFFSET,
            "vehicles": vehicles_list,
            "intersections": intersections,
            "metrics": self.metrics.snapshot(active_threads, len(vehicles_list), waiting),
            "events": list(self.event_log)[-30:],
        }
