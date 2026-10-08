"""
Métricas da tela /scheduling, separadas pela fase do semáforo (ON / OFF).

Diferente de `Metrics`, aqui os contadores têm Lock: o experimento é o
cruzamento, então a medição em si precisa ser confiável para a comparação
ON x OFF fazer sentido.
"""

from __future__ import annotations

import threading
import time


class _Bucket:
    def __init__(self) -> None:
        self.collisions = 0
        self.vehicles_involved = 0
        self.intersection_conflicts = 0
        self.vehicles_finished = 0
        self.vehicle_ticks = 0
        self.events_processed = 0

        self.wait_total = 0.0
        self.wait_samples = 0
        self.trip_total = {"emergency": 0.0, "normal": 0.0}
        self.trip_samples = {"emergency": 0, "normal": 0}

        self.elapsed = 0.0

    @staticmethod
    def _avg(total: float, n: int) -> float:
        return round(total / n, 2) if n else 0.0

    def snapshot(self, elapsed: float) -> dict:
        minutes = elapsed / 60 if elapsed > 0 else 0
        trips_total = self.trip_total["emergency"] + self.trip_total["normal"]
        trips_n = self.trip_samples["emergency"] + self.trip_samples["normal"]
        return {
            "collisions": self.collisions,
            "collisions_per_min": round(self.collisions / minutes, 2) if minutes else 0.0,
            "vehicles_involved": self.vehicles_involved,
            "intersection_conflicts": self.intersection_conflicts,
            "vehicles_finished": self.vehicles_finished,
            "average_wait_time": self._avg(self.wait_total, self.wait_samples),
            "average_trip_time": self._avg(trips_total, trips_n),
            "average_trip_time_emergency": self._avg(
                self.trip_total["emergency"], self.trip_samples["emergency"]
            ),
            "average_trip_time_normal": self._avg(
                self.trip_total["normal"], self.trip_samples["normal"]
            ),
            "elapsed": round(elapsed, 1),
        }


class SchedMetrics:
    """Mesma interface usada por Vehicle/collisions, roteada para a fase atual."""

    def __init__(self, sync_enabled: bool = False) -> None:
        self._lock = threading.Lock()
        self.start_time = time.time()
        self._buckets = {"on": _Bucket(), "off": _Bucket()}
        self._phase = "on" if sync_enabled else "off"
        self._phase_start = time.time()

        self.vehicles_spawned = 0
        self.peak_threads = 0
        self.paused_at: float | None = None

    @property
    def phase(self) -> str:
        return self._phase

    def _cur(self) -> _Bucket:
        return self._buckets[self._phase]

    def set_phase(self, sync_enabled: bool) -> None:
        new_phase = "on" if sync_enabled else "off"
        with self._lock:
            if new_phase == self._phase:
                return
            now = time.time()
            self._cur().elapsed += now - self._phase_start
            self._phase = new_phase
            self._phase_start = now

    def shift_time(self, dt: float) -> None:
        with self._lock:
            self.start_time += dt
            self._phase_start += dt

    def inc_spawned(self):
        with self._lock:
            self.vehicles_spawned += 1

    def inc_finished(self):
        with self._lock:
            self._cur().vehicles_finished += 1

    def inc_collisions(self, n: int = 1):
        with self._lock:
            self._cur().collisions += n

    def inc_vehicles_involved(self, n: int = 1):
        with self._lock:
            self._cur().vehicles_involved += n

    def inc_conflicts(self, n: int = 1):
        with self._lock:
            self._cur().intersection_conflicts += n

    def inc_events(self, n: int = 1):
        with self._lock:
            self._cur().events_processed += n

    def inc_tick(self, n: int = 1):
        with self._lock:
            self._cur().vehicle_ticks += n

    def add_wait_sample(self, wait_seconds: float):
        with self._lock:
            b = self._cur()
            b.wait_total += wait_seconds
            b.wait_samples += 1

    def add_trip_sample(self, trip_seconds: float, emergency: bool):
        key = "emergency" if emergency else "normal"
        with self._lock:
            b = self._cur()
            b.trip_total[key] += trip_seconds
            b.trip_samples[key] += 1

    def snapshot(self, active_threads: int, vehicles_alive: int, waiting: int) -> dict:
        with self._lock:
            self.peak_threads = max(self.peak_threads, active_threads)
            now = self.paused_at if self.paused_at is not None else time.time()
            phases = {}
            for name, bucket in self._buckets.items():
                elapsed = bucket.elapsed
                if name == self._phase:
                    elapsed += now - self._phase_start
                phases[name] = bucket.snapshot(elapsed)
            return {
                "phase": self._phase,
                "vehicles_total": self.vehicles_spawned,
                "vehicles_alive": vehicles_alive,
                "vehicles_waiting": waiting,
                "active_threads": active_threads,
                "peak_threads": self.peak_threads,
                "uptime": round(now - self.start_time, 1),
                "phases": phases,
            }
