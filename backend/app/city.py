import random
import threading
import time
from dataclasses import dataclass, field

from . import config


@dataclass
class Intersection:
    id: str
    h_index: int
    v_index: int
    x: float
    y: float

    occupied_by: str | None = None
    occupants: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)
    signal: object = field(default=None, repr=False, compare=False)

    def try_enter(self, vehicle_id: str) -> bool:
       
        was_free = len(self.occupants) == 0
        time.sleep(random.uniform(config.RACE_WINDOW_MIN, config.RACE_WINDOW_MAX))
        time.sleep(random.uniform(0.0005, 0.006))
        self.occupants.append(vehicle_id)
        self.occupied_by = vehicle_id
        raced = (
            was_free
            and len(self.occupants) > 1
            and self.occupants[-1] == vehicle_id
        )
        return raced

    def try_enter_signal(self, vehicle_id: str, approach: str, maneuver: str) -> bool:
        """
        Entrada controlada pelo semáforo: ler o sinal + entrar dentro do
        mesmo Lock que a thread controladora usa para trocar a fase.

        Não bloqueia: se o Lock estiver ocupado ou o sinal do movimento
        estiver fechado, retorna False e o veículo tenta no próximo tick.
        Assim o semáforo pode ser desligado a qualquer momento sem deixar
        thread presa no acquire().
        """
        if not self._lock.acquire(blocking=False):
            return False
        try:
            if self.signal is None or not self.signal.allows(approach, maneuver):
                return False
            self.occupants.append(vehicle_id)
            self.occupied_by = vehicle_id
            return True
        finally:
            self._lock.release()

    def step_signal(self, now: float) -> None:
        if self.signal is None:
            return
        with self._lock:
            self.signal.step(now)

    def leave(self, vehicle_id: str):
        try:
            self.occupants.remove(vehicle_id)
        except ValueError:
            pass


class City:
    def __init__(
        self,
        width: float = config.CITY_WIDTH,
        height: float = config.CITY_HEIGHT,
        horizontal_streets: list | None = None,
        vertical_streets: list | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.horizontal_streets = list(horizontal_streets or config.HORIZONTAL_STREETS)
        self.vertical_streets = list(vertical_streets or config.VERTICAL_STREETS)

        self.intersections: dict[tuple[int, int], Intersection] = {}
        for h_idx, y in enumerate(self.horizontal_streets):
            for v_idx, x in enumerate(self.vertical_streets):
                key = (h_idx, v_idx)
                self.intersections[key] = Intersection(
                    id=f"I_{h_idx}_{v_idx}", h_index=h_idx, v_index=v_idx, x=x, y=y
                )


    def snapshot(self) -> list[dict]:
        return [
            {
                "id": inter.id,
                "x": inter.x,
                "y": inter.y,
                "occupants": list(inter.occupants),
            }
            for inter in self.intersections.values()
        ]
