"""
Métricas da simulação.

IMPORTANTE (propositalmente): os contadores abaixo são incrementados
diretamente por várias Threads ao mesmo tempo, SEM Lock. Em CPython,
`x += 1` não é atômico (é um LOAD + ADD + STORE), então esses números
podem ocasionalmente "perder" incrementos sob alta concorrência. Isso
não é um bug a ser corrigido nesta versão — é parte da demonstração.
Na versão sincronizada, esta classe pode ganhar um `threading.Lock()`
sem que nenhum outro módulo precise mudar (todo acesso já passa por
métodos como `inc_collisions()`).
"""

import time


class Metrics:
    def __init__(self) -> None:
        self.start_time = time.time()

        self.vehicles_spawned = 0
        self.vehicles_finished = 0
        self.collisions = 0
        self.vehicles_involved = 0
        self.intersection_conflicts = 0   # race conditions detectadas no cruzamento
        self.events_processed = 0
        self.vehicle_ticks = 0
        self.overlap_events = 0

        self._wait_time_total = 0.0
        self._wait_time_samples = 0

    # ---- Sem lock de propósito: incrementos "sujos" ----
    def inc_spawned(self):
        self.vehicles_spawned += 1

    def inc_finished(self):
        self.vehicles_finished += 1

    def inc_collisions(self, n: int = 1):
        self.collisions += n

    def inc_vehicles_involved(self, n: int = 1):
        self.vehicles_involved += n

    def inc_conflicts(self, n: int = 1):
        self.intersection_conflicts += n

    def inc_events(self, n: int = 1):
        self.events_processed += n

    def inc_tick(self, n: int = 1):
        self.vehicle_ticks += n

    def inc_overlap(self, n: int = 1):
        self.overlap_events += n

    def add_wait_sample(self, wait_seconds: float):
        self._wait_time_total += wait_seconds
        self._wait_time_samples += 1

    @property
    def average_wait_time(self) -> float:
        if self._wait_time_samples == 0:
            return 0.0
        return self._wait_time_total / self._wait_time_samples

    @property
    def uptime(self) -> float:
        return time.time() - self.start_time

    @property
    def ticks_per_second(self) -> float:
        elapsed = self.uptime
        if elapsed <= 0:
            return 0.0
        return self.vehicle_ticks / elapsed

    def snapshot(self, active_threads: int, vehicles_alive: int, waiting: int) -> dict:
        return {
            "vehicles_total": self.vehicles_spawned,
            "vehicles_alive": vehicles_alive,
            "vehicles_finished": self.vehicles_finished,
            "vehicles_waiting": waiting,
            "active_threads": active_threads,
            "vehicle_ticks": self.vehicle_ticks,
            "ticks_per_second": round(self.ticks_per_second, 1),
            "overlap_events": self.overlap_events,
            "collisions": self.collisions,
            "vehicles_involved": self.vehicles_involved,
            "intersection_conflicts": self.intersection_conflicts,
            "events_processed": self.events_processed,
            "average_wait_time": round(self.average_wait_time, 3),
            "uptime": round(self.uptime, 1),
        }
