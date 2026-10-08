"""
SchedVehicle — veículo da tela /scheduling.

Sempre roda como Thread própria (multithread). Diferente do modo /threads:
  * anda na faixa do seu sentido (mão direita), com fila atrás de quem está à frente;
  * em cada cruzamento escolhe uma manobra: reto, direita ou esquerda;
  * semáforo OFF -> check-then-act sem lock (race possível);
  * semáforo ON  -> só entra quando o sinal do SEU movimento estiver verde
                    (`Intersection.try_enter_signal`); senão espera e tenta
                    no próximo tick.
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
    def __init__(self, *args, sync_enabled: Callable[[], bool], **kwargs):
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
    def _setup_route(self):
        super()._setup_route()
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
        return random.choices(options, weights=weights)[0]

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

        if self.sync_enabled():
            if not inter.try_enter_signal(self.id, approach, maneuver):
                if self.state != "waiting":
                    self._log(f"🔴 parado no semáforo de {inter.id}", level="wait")
                self._stop()
                return
        else:
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

        self._resume()
        self.metrics.add_wait_sample(self._stopped_total)
        self._stopped_total = 0.0

        self.movement = (approach, maneuver)
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
