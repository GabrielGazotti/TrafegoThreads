"""
Cada veículo é uma `threading.Thread` totalmente independente.

Não há Lock, Semaphore, Condition ou Event de coordenação entre veículos.
Cada Thread lê e escreve estado compartilhado (o dicionário de veículos,
os objetos `Intersection`) sem qualquer proteção — exatamente como pedido
no enunciado, para permitir Race Conditions, colisões e congestionamentos.
"""

from __future__ import annotations

import itertools
import random
import threading
import time

from . import config
from .city import City

_id_counter = itertools.count(1)


class Vehicle(threading.Thread):
    def __init__(
        self,
        city: City,
        registry: dict,
        event_log: list,
        metrics,
        stop_flag: threading.Event,
    ):
        vtype = random.choice(list(config.VEHICLE_TYPES.keys()))
        cfg = config.VEHICLE_TYPES[vtype]

        self.id = f"V{next(_id_counter)}"
        self.vtype = vtype
        self.emoji = cfg["emoji"]
        self.speed = cfg["speed"] * random.uniform(0.85, 1.25)     # variação individual
        self.tick_interval = cfg["tick"] * random.uniform(0.9, 1.15)
        self.aggressiveness = min(1.0, cfg["aggressiveness"] * random.uniform(0.6, 1.6))

        self.city = city
        self.registry = registry
        self.event_log = event_log
        self.metrics = metrics
        self.stop_flag = stop_flag

        self.axis = random.choice(["H", "V"])
        self.direction = random.choice([1, -1])
        self.state = "moving"
        self.crashed = False
        self.finished = False
        self.wait_start = None
        self.crash_time = None
        self.current_intersection = None  # (inter_key, cross_coord)
        self.crossing_pointer = 0

        self._setup_route()

        super().__init__(daemon=True, name=self.id)

    # ------------------------------------------------------------------
    def _setup_route(self):
        if self.axis == "H":
            self.h_index = random.randrange(len(self.city.horizontal_streets))
            self.y = self.city.horizontal_streets[self.h_index]
            self.x = -30.0 if self.direction == 1 else config.CITY_WIDTH + 30.0
            v_indices = range(len(self.city.vertical_streets))
            ordered = sorted(
                v_indices, key=lambda i: self.city.vertical_streets[i], reverse=self.direction == -1
            )
            self.crossings = [
                ((self.h_index, v_idx), self.city.vertical_streets[v_idx]) for v_idx in ordered
            ]
        else:
            self.v_index = random.randrange(len(self.city.vertical_streets))
            self.x = self.city.vertical_streets[self.v_index]
            self.y = -30.0 if self.direction == 1 else config.CITY_HEIGHT + 30.0
            h_indices = range(len(self.city.horizontal_streets))
            ordered = sorted(
                h_indices, key=lambda i: self.city.horizontal_streets[i], reverse=self.direction == -1
            )
            self.crossings = [
                ((h_idx, self.v_index), self.city.horizontal_streets[h_idx]) for h_idx in ordered
            ]

    def _log(self, message: str, level: str = "info"):
        self.event_log.append(
            {
                "t": round(time.time(), 3),
                "vehicle": self.id,
                "type": self.vtype,
                "level": level,
                "message": message,
            }
        )
        self.metrics.inc_events()

    # ------------------------------------------------------------------
    def run(self):
        while not self.stop_flag.is_set() and not self.crashed and not self.finished:
            try:
                self._tick()
            except Exception as exc:  # noqa: BLE001
                # Erros de corrida (ex.: estrutura mudou durante o acesso)
                # são esperados nesta versão sem sincronização — apenas
                # registramos e seguimos, sem travar a Thread.
                self._log(f"erro (possível race condition): {exc!r}", level="race")
            time.sleep(self.tick_interval)
        self._cleanup()

    def _tick(self):
        moving_coord = self.x if self.axis == "H" else self.y

        if self.current_intersection is not None:
            inter_key, cross_coord = self.current_intersection
            if abs(moving_coord - cross_coord) > config.INTERSECTION_RADIUS:
                inter = self.city.intersections[inter_key]
                inter.leave(self.id)
                self.current_intersection = None
                self.crossing_pointer += 1
            self._advance()
            return

        if self.crossing_pointer < len(self.crossings):
            inter_key, cross_coord = self.crossings[self.crossing_pointer]
            if abs(moving_coord - cross_coord) <= config.INTERSECTION_RADIUS:
                self._handle_intersection(inter_key, cross_coord)
                return

        self._advance()

    def _handle_intersection(self, inter_key, cross_coord):
        inter = self.city.intersections[inter_key]

        # Sem semáforo: cada veículo decide, de forma independente e
        # imprevisível, se hesita um instante antes de entrar (não é
        # sincronização — apenas comportamento individual). Isso ainda
        # cria congestionamento e aumenta a janela para a corrida abaixo.
        if random.random() < self.aggressiveness * 0.3 and self.state != "waiting":
            self.state = "waiting"
            self.wait_start = time.time()
            self._log(f"hesitou ao chegar em {inter.id}", level="wait")
            return
        if self.state == "waiting":
            self.metrics.add_wait_sample(time.time() - self.wait_start)
            self.wait_start = None

        # --- Ponto de corrida: check (was_free) e entrada não são atômicos ---
        was_free = inter.try_enter(self.id)
        if not was_free:
            self.metrics.inc_conflicts()
            self._log(
                f"⚠️ CONFLITO em {inter.id}: mais de um veículo entrou ao mesmo tempo",
                level="race",
            )

        self.state = "crossing"
        self.current_intersection = (inter_key, cross_coord)
        self._advance()

    def _advance(self):
        step = self.direction * self.speed * self.tick_interval
        if self.axis == "H":
            self.x += step
        else:
            self.y += step
        if self.state != "waiting":
            self.state = "crossing" if self.current_intersection else "moving"
        self._check_bounds()

    def _check_bounds(self):
        if self.axis == "H":
            out = self.x < -40 or self.x > config.CITY_WIDTH + 40
        else:
            out = self.y < -40 or self.y > config.CITY_HEIGHT + 40
        if out:
            self.state = "finished"
            self.finished = True
            self.metrics.inc_finished()

    def mark_crashed(self):
        """Chamado pelo monitor de colisões (outra Thread!) sem lock."""
        self.crashed = True
        self.state = "crashed"
        self.crash_time = time.time()

    def _cleanup(self):
        if self.current_intersection is not None:
            inter_key, _ = self.current_intersection
            self.city.intersections[inter_key].leave(self.id)
        if not self.crashed:
            # Remoção "suja": se outra Thread (monitor de colisão) mexeu no
            # registry ao mesmo tempo, pode dar KeyError — ignoramos.
            self.registry.pop(self.id, None)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.vtype,
            "emoji": self.emoji,
            "x": round(self.x, 1),
            "y": round(self.y, 1),
            "axis": self.axis,
            "direction": self.direction,
            "state": self.state,
            "crashed": self.crashed,
        }
