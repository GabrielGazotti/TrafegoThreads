from __future__ import annotations

import random
import threading
import time
from collections import deque

from .collisions import process_collision_clusters
from . import config
from .city import City
from .metrics import Metrics
from .vehicle import Vehicle


class SimulationManager:
    def __init__(self) -> None:
        self.city = City()
        self.metrics = Metrics()
        self.vehicles: dict[str,'Vehicle'] = {}
        self.event_log: deque = deque(maxlen=config.EVENT_LOG_MAXLEN)
        self.stop_flag = threading.Event()

        self._threads: list[threading.Thread] = []
        self._running = False
        self._overlap_active: set[str] = set()

    def start(self):
        if self._running:
            return
        self._running = True
        self.stop_flag.clear()

        spawner = threading.Thread(target=self._spawn_loop, name="spawner", daemon=True)
        collisions = threading.Thread(
            target=self._collision_monitor_loop, name="monitor-colisao", daemon=True
        )
        reaper = threading.Thread(target=self._reaper_loop, name="reaper", daemon=True)

        for t in (spawner, collisions, reaper):
            t.start()
            self._threads.append(t)

        self.event_log.append(
            {"t": time.time(), "vehicle": "-", "type": "sistema", "level": "info",
             "message": "Simulação iniciada (modo SEM sincronização)"}
        )

    def stop(self):
        self._running = False
        self.stop_flag.set()

    # ------------------------------------------------------------------
    def _spawn_loop(self):
        while not self.stop_flag.is_set():
            if len(self.vehicles) < config.MAX_VEHICLES:
                v = Vehicle(self.city, self.vehicles, self.event_log, self.metrics, self.stop_flag)
                self.vehicles[v.id] = v   # escrita direta no dict compartilhado
                self.metrics.inc_spawned()
                v.start_as_thread()
            time.sleep(random.uniform(config.SPAWN_INTERVAL_MIN, config.SPAWN_INTERVAL_MAX))

    def _collision_monitor_loop(self):
        while not self.stop_flag.is_set():
            try:
                snapshot = list(self.vehicles.values())
            except RuntimeError:
                time.sleep(config.COLLISION_CHECK_INTERVAL)
                continue

            active = [v for v in snapshot if not v.crashed and not v.finished]
            process_collision_clusters(active, self.city, self.metrics, self.event_log)

            time.sleep(config.COLLISION_CHECK_INTERVAL)

    def _reaper_loop(self):
        while not self.stop_flag.is_set():
            now = time.time()
            for vid, v in list(self.vehicles.items()):
                if v.finished or (v.crashed and v.crash_time and now - v.crash_time > config.CRASH_LINGER_TIME):
                    self.vehicles.pop(vid, None)
            time.sleep(0.5)

    def chaos_level(self, waiting: int) -> int:
        n_vehicles = len(self.vehicles)
        score = (
            n_vehicles * 1.2
            + waiting * 2.5
            + self.metrics.intersection_conflicts * 1.5
            + self.metrics.vehicles_involved * 8
        )
        return int(min(100, score))

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

        active_threads = self._count_active_threads()
        simultaneous = self._count_simultaneous_intersections()
        self._update_overlap_metrics()

        return {
            "mode": "multi",
            "vehicles": vehicles_list,
            "intersections": self.city.snapshot(),
            "metrics": self.metrics.snapshot(active_threads, len(vehicles_list), waiting),
            "utilization": {
                "execution_model": "parallel",
                "simultaneous_intersections": simultaneous,
                "overlap_events": self.metrics.overlap_events,
                "ticks_per_second": round(self.metrics.ticks_per_second, 1),
            },
            "chaos": self.chaos_level(waiting),
            "events": list(self.event_log)[-30:],
        }

    def _count_simultaneous_intersections(self) -> int:
        return sum(1 for inter in self.city.intersections.values() if len(inter.occupants) > 1)

    def _update_overlap_metrics(self) -> None:
        current = {
            inter.id
            for inter in self.city.intersections.values()
            if len(inter.occupants) > 1
        }
        for inter_id in current - self._overlap_active:
            self.metrics.inc_overlap()
        self._overlap_active = current

    def _count_active_threads(self) -> int:
        alive = sum(1 for v in self.vehicles.values() if not v.finished and not v.crashed)
        return 3 + alive
