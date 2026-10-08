"""
Semáforo de cruzamento com fases (modo scheduling) e matriz de conflitos.

Lados de chegada (approach): W, E, N, S  — de onde o veículo vem.
Manobras: "straight", "right", "left".

Ciclo de fases (conversão à esquerda protegida, um lado por vez, para quem
vira à esquerda nunca cruzar com quem vem de frente):
  1. N/S reto + direita
  2. N esquerda   (+ L/O direita)
  3. S esquerda   (+ L/O direita)
  4. L/O reto + direita
  5. L esquerda   (+ N/S direita)
  6. O esquerda   (+ N/S direita)
Entre fases: amarelo (ninguém novo entra) e vermelho geral (limpa o cruzamento).
"""

from __future__ import annotations

import time

from . import config

# heading em coordenadas de tela (y cresce para baixo)
APPROACH_HEADING = {"W": (1, 0), "E": (-1, 0), "N": (0, 1), "S": (0, -1)}
OPPOSITE = {"W": "E", "E": "W", "N": "S", "S": "N"}

def heading_of(axis: str, direction: int) -> tuple[int, int]:
    return (direction, 0) if axis == "H" else (0, direction)


def axis_dir_of(heading: tuple[int, int]) -> tuple[str, int]:
    dx, dy = heading
    return ("H", dx) if dx != 0 else ("V", dy)


def approach_of(axis: str, direction: int) -> str:
    if axis == "H":
        return "W" if direction == 1 else "E"
    return "N" if direction == 1 else "S"


def turn_heading(heading: tuple[int, int], maneuver: str) -> tuple[int, int]:
    dx, dy = heading
    if maneuver == "right":
        return (-dy, dx)
    if maneuver == "left":
        return (dy, -dx)
    return heading


def movements_conflict(m1: tuple[str, str] | None, m2: tuple[str, str] | None) -> bool:
    """
    Dois movimentos (approach, manobra) conflitam se cruzam ou se disputam
    a mesma faixa de saída. Mesmo lado de chegada = fila, não conflito.
    """
    if m1 is None or m2 is None:
        return False
    a1, man1 = m1
    a2, man2 = m2
    if a1 == a2:
        return False
    if turn_heading(APPROACH_HEADING[a1], man1) == turn_heading(APPROACH_HEADING[a2], man2):
        return True
    if man1 == "right" or man2 == "right":
        return False
    if OPPOSITE[a1] == a2:
        # reto x reto de frente usa faixas separadas; qualquer esquerda cruza a frente
        return not (man1 == "straight" and man2 == "straight")
    return True


THROUGH = frozenset({"straight", "right"})
LEFT = frozenset({"left"})
RIGHT = frozenset({"right"})

# (nome, {lado: manobras liberadas}, duração do verde)
PHASES = [
    ("N/S reto", {"N": THROUGH, "S": THROUGH}, config.SIGNAL_GREEN_THROUGH),
    ("N esquerda", {"N": LEFT, "E": RIGHT, "W": RIGHT}, config.SIGNAL_GREEN_LEFT),
    ("S esquerda", {"S": LEFT, "E": RIGHT, "W": RIGHT}, config.SIGNAL_GREEN_LEFT),
    ("L/O reto", {"E": THROUGH, "W": THROUGH}, config.SIGNAL_GREEN_THROUGH),
    ("L esquerda", {"E": LEFT, "N": RIGHT, "S": RIGHT}, config.SIGNAL_GREEN_LEFT),
    ("O esquerda", {"W": LEFT, "N": RIGHT, "S": RIGHT}, config.SIGNAL_GREEN_LEFT),
]


class TrafficSignal:
    """Estado do semáforo de um cruzamento. Avançado pela thread controladora."""

    def __init__(self, start_phase: int = 0, now: float | None = None) -> None:
        now = time.time() if now is None else now
        self.phase_idx = start_phase % len(PHASES)
        self.stage = "green"
        self.stage_end = now + PHASES[self.phase_idx][2]

    def step(self, now: float) -> None:
        while now >= self.stage_end:
            if self.stage == "green":
                self.stage = "yellow"
                self.stage_end += config.SIGNAL_YELLOW
            elif self.stage == "yellow":
                self.stage = "all_red"
                self.stage_end += config.SIGNAL_ALL_RED
            else:
                self.phase_idx = (self.phase_idx + 1) % len(PHASES)
                self.stage = "green"
                self.stage_end += PHASES[self.phase_idx][2]

    def allows(self, approach: str, maneuver: str) -> bool:
        _, allowed, _ = PHASES[self.phase_idx]
        return self.stage == "green" and maneuver in allowed.get(approach, ())

    def state(self) -> dict:
        """Cor de cada luz: {lado: {"left": cor, "straight": cor, "right": cor}}."""
        _, allowed, _ = PHASES[self.phase_idx]
        lit = {"green": "green", "yellow": "yellow"}.get(self.stage, "red")
        return {
            approach: {
                man: lit if man in allowed.get(approach, ()) else "red"
                for man in ("left", "straight", "right")
            }
            for approach in APPROACH_HEADING
        }
