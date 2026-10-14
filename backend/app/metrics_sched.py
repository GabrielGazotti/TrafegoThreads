"""
Métricas da tela /scheduling, separadas por modo de controle do cruzamento.

Cada modo tem seu balde: "off" (semáforo desligado) ou o algoritmo de
scheduling em uso ("fixed", "priority", "fcfs", ...). Todo evento é contado
no balde do modo ativo no momento do evento.

Médias e máximos sem nenhuma amostra saem como None (a tela mostra "—"), para
não confundir "sem dados" com "zero". A vazão só aparece depois de
SCHED_MIN_ELAPSED_FOR_RATE segundos no modo.

Diferente de `Metrics`, aqui os contadores têm Lock: o experimento é o
cruzamento, então a medição em si precisa ser confiável para a comparação
entre os modos fazer sentido.
"""

from __future__ import annotations

import threading
import time

from . import config

CATEGORIES = ("emergency", "normal")


def _cat(emergency: bool) -> str:
    return "emergency" if emergency else "normal"


class _Bucket:
    def __init__(self, label: str) -> None:
        self.label = label
        self.collisions = 0
        self.vehicles_involved = 0
        self.intersection_conflicts = 0
        self.vehicles_finished = 0
        self.vehicle_ticks = 0
        self.events_processed = 0
        self.preemptions = 0

        self.wait_total = {c: 0.0 for c in CATEGORIES}
        self.wait_samples = {c: 0 for c in CATEGORIES}
        self.wait_max = {c: 0.0 for c in CATEGORIES}
        self.trip_total = {c: 0.0 for c in CATEGORIES}
        self.trip_samples = {c: 0 for c in CATEGORIES}

        self.elapsed = 0.0

    @staticmethod
    def _avg(total: float, n: int) -> float | None:
        return round(total / n, 2) if n else None

    def _max(self, *cats: str) -> float | None:
        if not any(self.wait_samples[c] for c in cats):
            return None
        return round(max(self.wait_max[c] for c in cats), 2)

    def snapshot(self, elapsed: float) -> dict:
        minutes = elapsed / 60
        has_rate = elapsed >= config.SCHED_MIN_ELAPSED_FOR_RATE
        wait_total = sum(self.wait_total.values())
        wait_n = sum(self.wait_samples.values())
        trips_total = sum(self.trip_total.values())
        trips_n = sum(self.trip_samples.values())
        return {
            "label": self.label,
            "collisions": self.collisions,
            "collisions_per_min": round(self.collisions / minutes, 2) if has_rate else None,
            "vehicles_involved": self.vehicles_involved,
            "intersection_conflicts": self.intersection_conflicts,
            "vehicles_finished": self.vehicles_finished,
            "throughput_per_min": round(self.vehicles_finished / minutes, 1) if has_rate else None,
            "preemptions": self.preemptions,
            "average_wait_time": self._avg(wait_total, wait_n),
            "average_wait_time_emergency": self._avg(
                self.wait_total["emergency"], self.wait_samples["emergency"]
            ),
            "average_wait_time_normal": self._avg(
                self.wait_total["normal"], self.wait_samples["normal"]
            ),
            "max_wait_time": self._max(*CATEGORIES),
            "max_wait_time_emergency": self._max("emergency"),
            "max_wait_time_normal": self._max("normal"),
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
    """Mesma interface usada por Vehicle/collisions, roteada para o modo atual."""

    def __init__(self, mode: str = "off", label: str = "Semáforo OFF") -> None:
        self._lock = threading.Lock()
        self.start_time = time.time()
        # dict mantém a ordem em que os modos foram usados
        self._buckets: dict[str, _Bucket] = {mode: _Bucket(label)}
        self._phase = mode
        self._phase_start = time.time()

        self.vehicles_spawned = 0
        self.peak_threads = 0
        self.paused_at: float | None = None

    @property
    def phase(self) -> str:
        return self._phase

    def _cur(self) -> _Bucket:
        return self._buckets[self._phase]

    def set_phase(self, mode: str, label: str) -> None:
        with self._lock:
            if mode == self._phase:
                return
            now = self.paused_at if self.paused_at is not None else time.time()
            self._cur().elapsed += now - self._phase_start
            if mode not in self._buckets:
                self._buckets[mode] = _Bucket(label)
            self._phase = mode
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

    def inc_preemptions(self, n: int = 1):
        with self._lock:
            self._cur().preemptions += n

    def add_wait_sample(self, wait_seconds: float, emergency: bool = False):
        key = _cat(emergency)
        with self._lock:
            b = self._cur()
            b.wait_total[key] += wait_seconds
            b.wait_samples[key] += 1
            b.wait_max[key] = max(b.wait_max[key], wait_seconds)

    def add_trip_sample(self, trip_seconds: float, emergency: bool):
        key = _cat(emergency)
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
