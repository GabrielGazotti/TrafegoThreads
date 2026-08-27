"""
SimulationManager — orquestra as Threads da simulação SEM SINCRONIZAÇÃO.

Threads criadas por este módulo:
  * 1 Thread "spawner"        -> cria novos veículos continuamente
  * 1 Thread "semáforos"      -> atualiza o estado dos cruzamentos
  * 1 Thread "monitor de colisão" -> varre os veículos e detecta colisões
  * N Threads "veículo"       -> uma por veículo (ver vehicle.py)

Nenhuma dessas Threads usa Lock/Semaphore/Condition/Event para se
coordenar com as outras. O `threading.Event` `self.stop_flag` é usado
apenas para PARAR a simulação de forma limpa (shutdown), não para
sincronizar acesso a recursos — por isso seu uso não viola o requisito.

PONTO DE EXTENSÃO FUTURO
-------------------------
Para a versão sincronizada, a ideia é criar um `simulation_sync.py` que
reaproveite `City`, `Vehicle` e `Metrics`, apenas trocando:
  - `Intersection.try_enter/leave` por versões com `threading.Lock`
  - os contadores de `Metrics` por versões protegidas por Lock
sem precisar tocar no resto da arquitetura (FastAPI, WebSocket, React).
"""

from __future__ import annotations

import itertools
import random
import threading
import time
from collections import deque

from . import config
from .city import City
from .metrics import Metrics
from .vehicle import Vehicle


class SimulationManager:
    def __init__(self) -> None:
        self.city = City()
        self.metrics = Metrics()
        self.vehicles: dict[str, Vehicle] = {}   # estado compartilhado, sem lock
        self.event_log: deque = deque(maxlen=config.EVENT_LOG_MAXLEN)
        self.stop_flag = threading.Event()

        self._threads: list[threading.Thread] = []
        self._running = False

    # ------------------------------------------------------------------
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
                v.start()
            time.sleep(random.uniform(config.SPAWN_INTERVAL_MIN, config.SPAWN_INTERVAL_MAX))

    def _collision_monitor_loop(self):
        """
        Varre os veículos vivos e verifica proximidade excessiva entre
        veículos que estão no mesmo cruzamento (ou muito próximos na
        mesma rua). Isso é feito lendo o dicionário `self.vehicles`
        enquanto outras Threads o modificam ao mesmo tempo -> possível
        fonte adicional de inconsistência, tratada apenas com try/except.
        """
        while not self.stop_flag.is_set():
            try:
                snapshot = list(self.vehicles.values())
            except RuntimeError:
                # dict mudou de tamanho durante a iteração -> race condition
                # esperada; simplesmente tenta de novo no próximo ciclo.
                time.sleep(config.COLLISION_CHECK_INTERVAL)
                continue

            active = [v for v in snapshot if not v.crashed and not v.finished]

            for a, b in itertools.combinations(active, 2):
                if a.crashed or b.crashed:
                    continue
                dist = ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5
                same_zone = (
                    a.current_intersection is not None
                    and b.current_intersection is not None
                    and a.current_intersection[0] == b.current_intersection[0]
                ) or dist < config.COLLISION_DISTANCE

                if same_zone and dist < config.COLLISION_DISTANCE:
                    a.mark_crashed()
                    b.mark_crashed()
                    self.metrics.inc_collisions()
                    inter_desc = (
                        self.city.intersections[a.current_intersection[0]].id
                        if a.current_intersection
                        else "via"
                    )
                    self.event_log.append(
                        {
                            "t": round(time.time(), 3),
                            "vehicle": f"{a.id}+{b.id}",
                            "type": "colisao",
                            "level": "crash",
                            "message": f"💥 COLISÃO entre {a.id} e {b.id} perto de {inter_desc}",
                        }
                    )
                    self.metrics.inc_events()

            time.sleep(config.COLLISION_CHECK_INTERVAL)

    def _reaper_loop(self):
        """Remove do dicionário veículos 'finished' ou 'crashed' há tempo
        suficiente. Também sem lock: pode colidir com o próprio veículo
        tentando se auto-remover em `_cleanup()` — por isso o try/except."""
        while not self.stop_flag.is_set():
            now = time.time()
            for vid, v in list(self.vehicles.items()):
                if v.finished or (v.crashed and v.crash_time and now - v.crash_time > config.CRASH_LINGER_TIME):
                    self.vehicles.pop(vid, None)
            time.sleep(0.5)

    # ------------------------------------------------------------------
    def chaos_level(self, waiting: int) -> int:
        """Índice de 0 a 100 usado pelo frontend para o indicador de CAOS.
        Combinação simples de: veículos ativos, conflitos, colisões e
        veículos esperando. Não precisa ser cientificamente exato — é um
        termômetro visual do quão "bagunçada" está a simulação."""
        n_vehicles = len(self.vehicles)
        score = (
            n_vehicles * 1.2
            + waiting * 2.5
            + self.metrics.intersection_conflicts * 1.5
            + self.metrics.collisions * 8
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

        active_threads = threading.active_count()

        return {
            "vehicles": vehicles_list,
            "intersections": self.city.snapshot(),
            "metrics": self.metrics.snapshot(active_threads, len(vehicles_list), waiting),
            "chaos": self.chaos_level(waiting),
            "events": list(self.event_log)[-30:],
        }
