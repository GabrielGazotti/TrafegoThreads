import random
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

    def try_enter(self, vehicle_id: str) -> bool:
        """
        Check-then-act sem lock. Sempre entra.

        Retorna True só na race: este veículo leu o cruzamento livre, mas
        na hora do append já havia outro — outra thread leu vazio na mesma
        janela. Fila (entrou com alguém já dentro) retorna False.
        """
        was_free = len(self.occupants) == 0
        time.sleep(random.uniform(0.0005, 0.006))
        self.occupants.append(vehicle_id)
        self.occupied_by = vehicle_id
        raced = (
            was_free
            and len(self.occupants) > 1
            and self.occupants[-1] == vehicle_id
        )
        return raced

    def leave(self, vehicle_id: str):
        try:
            self.occupants.remove(vehicle_id)
        except ValueError:
            pass


class City:
    def __init__(self) -> None:
        self.horizontal_streets = list(config.HORIZONTAL_STREETS)
        self.vertical_streets = list(config.VERTICAL_STREETS)

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
