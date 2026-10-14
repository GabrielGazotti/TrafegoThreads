"""
SchedVehicle — veículo da tela /scheduling.

Sempre roda como Thread própria (multithread). Diferente do modo /threads:
  * anda na faixa do seu sentido (mão direita), com fila atrás de quem está à frente;
  * em cada cruzamento escolhe uma manobra: reto, direita ou esquerda;
  * semáforo OFF -> check-then-act sem lock (race possível);
  * semáforo ON  -> pede a vez ao escalonador do cruzamento
                    (`Intersection.try_enter_sched`) com seu movimento,
                    prioridade e tempo de travessia; se negado, espera e
                    renova o pedido no próximo tick.

Tudo que define o veículo (velocidade, rua, sentido, manobras) sai do gerador
`rng` próprio dele. No modo comparação, cada simulação recebe as mesmas seeds,
então todas veem exatamente o mesmo fluxo de veículos.
"""

from __future__ import annotations

import itertools
import random
import time
from typing import Callable

from . import config
from .signals import approach_of, axis_dir_of, heading_of, turn_heading
from .vehicle import Vehicle

_sched_id_counter = itertools.count(1)


def reset_sched_id_counter() -> None:
    global _sched_id_counter
    _sched_id_counter = itertools.count(1)


def lane_coord(axis: str, direction: int, street: float, left_lane: bool = False) -> float:
    """
    Coordenada perpendicular da faixa, à direita de quem anda.
    `left_lane` = faixa de dentro, exclusiva de quem vai converter à esquerda.
    """
    L = config.SCHED_LEFT_LANE_OFFSET if left_lane else config.SCHED_LANE_OFFSET
    return street + direction * L if axis == "H" else street - direction * L


class SchedVehicle(Vehicle):
    def __init__(self, *args, sync_enabled: Callable[[], bool],
                 rng: random.Random | None = None, **kwargs):
        # precisa existir antes do super().__init__, que chama _setup_route()
        self.rng = rng or random.Random()
        super().__init__(
            *args,
            vehicle_types=config.SCHED_VEHICLE_TYPES,
            vehicle_id=f"S{next(_sched_id_counter)}",
            **kwargs,
        )
        self.sync_enabled = sync_enabled

    @property
    def is_emergency(self) -> bool:
        return self.priority >= config.PRIORITY_EMERGENCY

    # ------------------------------------------------------------------ rota
    def _roll_identity(self) -> None:
        """Sorteia (com `self.rng`) o que a classe base sorteou com `random`."""
        rng = self.rng
        cfg = config.SCHED_VEHICLE_TYPES[self.vtype]
        self.speed = cfg["speed"] * rng.uniform(0.85, 1.25)
        self.tick_interval = cfg["tick"] * rng.uniform(0.9, 1.15)
        self.aggressiveness = min(1.0, cfg["aggressiveness"] * rng.uniform(0.6, 1.6))
        self.axis = rng.choice(["H", "V"])
        self.direction = rng.choice([1, -1])

        if self.axis == "H":
            self.h_index = rng.randrange(len(self.city.horizontal_streets))
            self.y = self.city.horizontal_streets[self.h_index]
            self.x = -30.0 if self.direction == 1 else self.city.width + 30.0
            items = [((self.h_index, v), x) for v, x in enumerate(self.city.vertical_streets)]
        else:
            self.v_index = rng.randrange(len(self.city.vertical_streets))
            self.x = self.city.vertical_streets[self.v_index]
            self.y = -30.0 if self.direction == 1 else self.city.height + 30.0
            items = [((h, self.v_index), y) for h, y in enumerate(self.city.horizontal_streets)]
        self.crossings = sorted(items, key=lambda it: it[1] * self.direction)

    def _setup_route(self):
        self._roll_identity()
        if self.axis == "H":
            self.y = lane_coord("H", self.direction, self.y)
        else:
            self.x = lane_coord("V", self.direction, self.x)

        self.turns_done = 0
        self.next_maneuver = self._pick_maneuver()
        self.movement: tuple[str, str] | None = None
        self.turn_target: float | None = None
        self._turned_here = False
        self._in_left_lane = False
        self._stop_since: float | None = None
        self._stopped_total = 0.0

    def _pick_maneuver(self) -> str:
        if self.turns_done >= config.SCHED_MAX_TURNS:
            return "straight"
        options = list(config.SCHED_TURN_PROBS)
        weights = [config.SCHED_TURN_PROBS[o] for o in options]
        return self.rng.choices(options, weights=weights)[0]

    def _crossings_for(self, axis: str, direction: int, inter_key) -> list:
        h_idx, v_idx = inter_key
        if axis == "H":
            items = [((h_idx, v), self.city.vertical_streets[v])
                     for v in range(len(self.city.vertical_streets))]
            center = self.city.vertical_streets[v_idx]
        else:
            items = [((h, v_idx), self.city.horizontal_streets[h])
                     for h in range(len(self.city.horizontal_streets))]
            center = self.city.horizontal_streets[h_idx]
        ahead = [it for it in items if (it[1] - center) * direction > 0]
        return sorted(ahead, key=lambda it: it[1] * direction)

    # ------------------------------------------------------------ helpers
    def _moving(self) -> float:
        return self.x if self.axis == "H" else self.y

    def _lane(self) -> float:
        return self.y if self.axis == "H" else self.x

    def _stop(self):
        if self._stop_since is None:
            self._stop_since = time.time()
        self.state = "waiting"

    def _resume(self):
        if self._stop_since is not None:
            self._stopped_total += time.time() - self._stop_since
            self._stop_since = None
        if self.state == "waiting":
            self.state = "moving"

    def _lane_has_vehicle(self, lane: float, behind: float, ahead: float) -> bool:
        """Há veículo na faixa `lane` entre `behind` atrás e `ahead` à frente?"""
        my_moving = self._moving()
        for other in list(self.registry.values()):
            if other is self or other.finished:
                continue
            if other.axis != self.axis or other.direction != self.direction:
                continue
            if abs(other._lane() - lane) > 1:
                continue
            gap = (other._moving() - my_moving) * self.direction
            if -behind < gap < ahead:
                return True
        return False

    def _blocked_ahead(self) -> bool:
        return self._lane_has_vehicle(self._lane(), 0, config.SCHED_FOLLOW_GAP)

    def _street(self) -> float:
        if self.axis == "H":
            return self.city.horizontal_streets[self.h_index]
        return self.city.vertical_streets[self.v_index]

    def _try_enter_left_lane(self) -> None:
        """Perto do cruzamento, quem vai virar à esquerda passa para a faixa de dentro."""
        if self.next_maneuver != "left" or self._in_left_lane:
            return
        if self.crossing_pointer >= len(self.crossings):
            return
        _, cross_coord = self.crossings[self.crossing_pointer]
        dist = (cross_coord - self._moving()) * self.direction
        if dist > config.INTERSECTION_RADIUS + config.SCHED_LEFT_POCKET:
            return
        target = lane_coord(self.axis, self.direction, self._street(), left_lane=True)
        gap = config.SCHED_FOLLOW_GAP
        if self._lane_has_vehicle(target, gap, gap):
            return
        if self.axis == "H":
            self.y = target
        else:
            self.x = target
        self._in_left_lane = True

    # --------------------------------------------------------------- tick
    def _tick(self):
        if self.current_intersection is not None:
            self._tick_inside()
            return

        self._try_enter_left_lane()
        if self._blocked_ahead():
            self._stop()
            return

        if self.crossing_pointer < len(self.crossings):
            inter_key, cross_coord = self.crossings[self.crossing_pointer]
            if (cross_coord - self._moving()) * self.direction <= config.INTERSECTION_RADIUS:
                self._handle_intersection(inter_key, cross_coord)
                return

        self._resume()
        self._advance()

    def _handle_intersection(self, inter_key, cross_coord):
        inter = self.city.intersections[inter_key]
        approach = approach_of(self.axis, self.direction)
        maneuver = self.next_maneuver

        movement = (approach, maneuver)
        if self.sync_enabled():
            if not inter.try_enter_sched(self.id, movement, self.priority,
                                         f"{self.emoji} {self.id}"):
                if self.state != "waiting":
                    self._log(f"🔴 aguardando a vez em {inter.id}", level="wait")
                self._stop()
                return
        else:
            # hesitação usa o `random` global de propósito: depende do timing das
            # threads e não pode desalinhar a sequência de manobras do `self.rng`
            if random.random() < self.aggressiveness * 0.3 and self.state != "waiting":
                self._stop()
                self._log(f"hesitou ao chegar em {inter.id}", level="wait")
                return
            if inter.try_enter(self.id):
                self.metrics.inc_conflicts()
                self._log(
                    f"⚠️ RACE em {inter.id}: duas threads leram o cruzamento livre",
                    level="race",
                )
            # registra o movimento mesmo sem lock: se o semáforo for ligado com
            # este veículo dentro, o escalonador precisa saber que ele está lá
            inter.occupant_moves[self.id] = movement

        self._resume()
        self.metrics.add_wait_sample(self._stopped_total, self.is_emergency)
        self._stopped_total = 0.0

        self.movement = movement
        self.current_intersection = (inter_key, cross_coord)
        self._turned_here = False
        if maneuver != "straight":
            new_axis, new_dir = axis_dir_of(turn_heading(heading_of(self.axis, self.direction), maneuver))
            street = inter.x if new_axis == "V" else inter.y
            self.turn_target = lane_coord(new_axis, new_dir, street)
        self.state = "crossing"
        self._advance()

    def _tick_inside(self):
        inter_key, cross_coord = self.current_intersection
        inter = self.city.intersections[inter_key]

        if self.turn_target is not None and (self._moving() - self.turn_target) * self.direction >= 0:
            self._execute_turn(inter_key, inter)
            cross_coord = self.current_intersection[1]

        if (self._moving() - cross_coord) * self.direction > config.INTERSECTION_RADIUS:
            inter.leave(self.id)
            self.current_intersection = None
            self.movement = None
            self._in_left_lane = False
            if not self._turned_here:
                self.crossing_pointer += 1
            self.next_maneuver = self._pick_maneuver()

        self._advance()

    def _execute_turn(self, inter_key, inter):
        new_heading = turn_heading(heading_of(self.axis, self.direction), self.next_maneuver)
        new_axis, new_dir = axis_dir_of(new_heading)
        if self.axis == "H":
            self.x = self.turn_target
        else:
            self.y = self.turn_target
        self.axis, self.direction = new_axis, new_dir
        if new_axis == "H":
            self.h_index = inter_key[0]
        else:
            self.v_index = inter_key[1]

        self.crossings = self._crossings_for(new_axis, new_dir, inter_key)
        self.crossing_pointer = 0
        self.current_intersection = (inter_key, inter.x if new_axis == "H" else inter.y)
        self.turn_target = None
        self.turns_done += 1
        self._turned_here = True

    def _advance(self):
        step = self.direction * self.speed * self.tick_interval
        if self.axis == "H":
            self.x += step
        else:
            self.y += step
        if self.state != "waiting":
            self.state = "crossing" if self.current_intersection else "moving"
        self._check_bounds()

    def shift_time(self, dt: float) -> None:
        super().shift_time(dt)
        if self._stop_since is not None:
            self._stop_since += dt

    def _check_bounds(self):
        was_finished = self.finished
        super()._check_bounds()
        if self.finished and not was_finished:
            self.metrics.add_trip_sample(time.time() - self.spawn_time, self.is_emergency)

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["emergency"] = self.is_emergency
        d["maneuver"] = self.next_maneuver
        return d
