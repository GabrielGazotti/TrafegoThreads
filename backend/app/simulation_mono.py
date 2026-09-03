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


class SimulationManagerMono:
    def __init__(self) -> None:
        self.city = City()
        self.metrics = Metrics()
        self.vehicles: dict[str, Vehicle] = {}
        self.event_log: deque = deque(maxlen=config.EVENT_LOG_MAXLEN)
        self.stop_flag = threading.Event()

        self.ticking_id: str | None = None
        self._loop_thread: threading.Thread | None = None
        self._running = False
        self._overlap_active: set[str] = set()

    def start(self):
        if self._running:
            return
        self._running = True
        self.stop_flag.clear()
        self._loop_thread = threading.Thread(target=self._main_loop, name="sim-mono", daemon=True)
        self._loop_thread.start()
        self.event_log.append(
            {
                "t": time.time(),
                "vehicle": "-",
                "type": "sistema",
                "level": "info",
                "message": "Simulação MONO iniciada (1 thread sequencial)",
            }
        )

    def stop(self):
        self._running = False
        self.stop_flag.set()

    def _main_loop(self):
        last_spawn = time.time()
        last_reap = time.time()

        while not self.stop_flag.is_set():
            cycle_start = time.time()

            # spawn
            now = time.time()
            if now - last_spawn >= random.uniform(config.SPAWN_INTERVAL_MIN, config.SPAWN_INTERVAL_MAX):
                if len(self.vehicles) < config.MAX_VEHICLES:
                    v = Vehicle(self.city, self.vehicles, self.event_log, self.metrics)
                    self.vehicles[v.id] = v
                    self.metrics.inc_spawned()
                last_spawn = now

            # tick sequencial — um veículo por vez
            for vid, v in list(self.vehicles.items()):
                if v.finished or v.crashed:
                    continue
                self.ticking_id = vid
                v.tick_once()
            self.ticking_id = None

            self._check_collisions()

            # reaper
            now_reap = time.time()
            if now_reap - last_reap > 0.5:
                for vid, v in list(self.vehicles.items()):
                    if v.finished or (
                        v.crashed and v.crash_time and now_reap - v.crash_time > config.CRASH_LINGER_TIME
                    ):
                        if v.current_intersection is not None:
                            inter_key, _ = v.current_intersection
                            self.city.intersections[inter_key].leave(v.id)
                        self.vehicles.pop(vid, None)
                last_reap = now_reap

            elapsed = time.time() - cycle_start
            sleep_time = max(0.01, config.BROADCAST_INTERVAL - elapsed)
            time.sleep(sleep_time)

    def _check_collisions(self):
        active = [v for v in self.vehicles.values() if not v.crashed and not v.finished]
        process_collision_clusters(active, self.city, self.metrics, self.event_log)

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

        simultaneous = self._count_simultaneous_intersections()
        self._update_overlap_metrics()

        return {
            "mode": "mono",
            "ticking_id": self.ticking_id,
            "vehicles": vehicles_list,
            "intersections": self.city.snapshot(),
            "metrics": self.metrics.snapshot(1, len(vehicles_list), waiting),
            "utilization": {
                "execution_model": "sequential",
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
