"""
Ciclo de vida das simulações: idle -> running <-> paused -> stopped.

Pausar = limpar o `run_gate` (threading.Event). Todas as threads da simulação
(veículos, spawner, monitor, reaper, semáforos, loop MONO) chamam
`run_gate.wait()` antes de cada passo, então ficam bloqueadas sem gastar CPU.
Ao continuar, os relógios internos (métricas, spawn, espera, semáforos) são
avançados pelo tempo pausado, para a pausa não contar nas métricas.
"""

from __future__ import annotations

import threading
import time


class Lifecycle:
    def _init_lifecycle(self) -> None:
        self.stop_flag = threading.Event()
        self.run_gate = threading.Event()
        self.status = "idle"
        # o tempo parado antes do primeiro start também não conta
        self._paused_at: float | None = time.time()
        self.metrics.paused_at = self._paused_at

    def _launch(self) -> None:
        raise NotImplementedError

    def start(self) -> None:
        if self.status == "running" or self.status == "stopped":
            return
        if self._paused_at is not None:
            self._shift_time(time.time() - self._paused_at)
            self._paused_at = None
            self.metrics.paused_at = None
        first_start = self.status == "idle"
        self.status = "running"
        self.run_gate.set()
        if first_start:
            self._launch()

    def pause(self) -> None:
        if self.status != "running":
            return
        self.run_gate.clear()
        self._paused_at = time.time()
        self.metrics.paused_at = self._paused_at
        self.status = "paused"

    def stop(self) -> None:
        self.status = "stopped"
        self.stop_flag.set()
        self.run_gate.set()

    def _wait_running(self) -> bool:
        """Bloqueia enquanto pausado. Retorna False se a simulação foi encerrada."""
        self.run_gate.wait()
        return not self.stop_flag.is_set()

    def _shift_time(self, dt: float) -> None:
        self.metrics.shift_time(dt)
        for v in list(self.vehicles.values()):
            v.shift_time(dt)
