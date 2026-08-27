"""
Modelo da cidade: ruas horizontais/verticais e cruzamentos.

PONTO DE SINCRONIZAÇÃO FUTURO
------------------------------
As duas operações abaixo, `try_enter()` e `leave()`, são exatamente os
pontos onde a versão sincronizada vai inserir um `threading.Lock`
(um Lock por cruzamento). Propositalmente, nesta versão elas fazem
"check-then-act" sem nenhuma proteção:

    Thread A -> lê occupied_by (None)         )
    Thread B -> lê occupied_by (None)         ) mesma janela de tempo
    Thread A -> escreve occupied_by = "A"     )
    Thread B -> escreve occupied_by = "B"     ) <- corrida de dados!

Isso é feito de propósito e não deve ser "corrigido" aqui.
"""

import random
import time
from dataclasses import dataclass, field

from . import config


@dataclass
class Intersection:
    id: str
    h_index: int          # índice da rua horizontal
    v_index: int          # índice da rua vertical
    x: float
    y: float

    # --- Estado compartilhado e DELIBERADAMENTE não protegido ---
    occupied_by: str | None = None     # último veículo "dono" do cruzamento
    occupants: list = field(default_factory=list)   # veículos dentro do cruzamento agora

    # ---- Operações DE PROPÓSITO sem lock ----
    def try_enter(self, vehicle_id: str) -> bool:
        """
        Verifica se o cruzamento "parece" livre e entra.
        Entre o `if` e o `append`, outra Thread pode fazer a mesma coisa:
        esse é o gap de corrida citado no enunciado.
        """
        was_free = len(self.occupants) == 0
        time.sleep(random.uniform(0.0005, 0.006))
        self.occupants.append(vehicle_id)
        self.occupied_by = vehicle_id
        return was_free

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
