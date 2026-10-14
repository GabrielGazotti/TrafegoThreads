"""
Escalonadores do cruzamento (tela /scheduling, semáforo ligado).

Analogia com escalonamento de CPU:
  * o "processador" é o verde: só uma fase do semáforo roda por vez;
  * os "processos" são os veículos parados na linha de retenção (fila de prontos);
  * a troca de fase (amarelo + vermelho geral) é a "troca de contexto".

Os três algoritmos usam o MESMO semáforo de 6 fases (`signals.PHASES`) — só muda
a política que escolhe a próxima fase. Assim a comparação mede a política, não
o modelo de cruzamento.

  * "fixed"    — ciclo fixo: as fases sempre na mesma ordem (round-robin de fases).
  * "fcfs"     — First Come, First Served: no fim de cada vermelho geral abre a
                 fase de quem chegou primeiro na fila. Não preemptivo.
  * "priority" — fila de prioridade: abre a fase do pedido mais prioritário.
                 Preemptivo (opcional): emergência no vermelho corta o verde atual.
                 Aging (opcional): a prioridade efetiva cresce com a espera.

Pedido de passagem (`Request`): o veículo da frente de cada faixa, ao chegar
na linha de retenção, registra (movimento, prioridade, chegada) e renova o
pedido a cada tick até entrar. A fila é um `heapq` por cruzamento, acessado
sempre dentro do `threading.Lock` do cruzamento.

Regra de segurança comum: só entra quem tem verde E não conflita (matriz de
`movements_conflict`) com nenhum veículo que já está dentro do cruzamento.
"""

from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass
from typing import Callable

from . import config
from .signals import PHASES, TrafficSignal, movements_conflict, phase_for


@dataclass
class Request:
    vid: str
    movement: tuple[str, str]
    priority: int
    arrival: float
    seq: int
    last_seen: float
    label: str = ""


class SignalController:
    def __init__(self, now: float, policy: str = "fixed", preemption: bool = False,
                 aging: bool = False, on_event: Callable[[str, str], None] | None = None) -> None:
        self.algorithm = policy
        self.signal = TrafficSignal(start_phase=0, now=now, phases=PHASES)
        self.uses_queue = policy in ("fcfs", "priority")
        self.preemption = policy == "priority" and preemption
        self.aging = policy == "priority" and aging
        self.requests: dict[str, Request] = {}
        self._seq = itertools.count()
        self._on_event = on_event or (lambda kind, msg: None)
        # heap de (chave, seq, vid) com remoção preguiçosa: entradas de pedidos
        # que já saíram são descartadas quando chegam ao topo. Ver `_key`.
        self._heap: list[tuple[float, int, str]] = []

    # ------------------------------------------------------------ pedidos
    def request(self, vid: str, movement, priority: int, now: float,
                label: str = "") -> Request:
        r = self.requests.get(vid)
        if r is None or r.movement != movement:
            r = Request(vid, movement, priority, now, next(self._seq), now, label)
            self.requests[vid] = r
            if self.uses_queue:
                heapq.heappush(self._heap, (self._key(r), r.seq, r.vid))
        else:
            r.last_seen = now
        return r

    def _expire(self, now: float) -> None:
        ttl = config.SCHED_REQUEST_TTL
        for vid in [v for v, r in self.requests.items() if now - r.last_seen > ttl]:
            del self.requests[vid]

    # -------------------------------------------------- fila (heapq)
    def _key(self, r: Request) -> float:
        """
        FCFS: instante de chegada.
        Prioridade sem aging: -prioridade (empate: ordem de chegada pelo seq).
        Prioridade com aging: prioridade efetiva = prioridade + (agora - chegada) * taxa.
          Ordenar por -efetiva = chegada * taxa - prioridade - agora * taxa;
          o último termo é igual para todos, então a chave
          `chegada * taxa - prioridade` não muda com o tempo e cabe no heapq.
        """
        if self.algorithm == "fcfs":
            return r.arrival
        if self.aging:
            return r.arrival * config.SCHED_AGING_RATE - r.priority
        return -r.priority

    def _effective(self, r: Request, now: float) -> float:
        if self.aging:
            return r.priority + (now - r.arrival) * config.SCHED_AGING_RATE
        return r.priority

    def _top(self) -> Request | None:
        while self._heap:
            _, seq, vid = self._heap[0]
            r = self.requests.get(vid)
            if r is not None and r.seq == seq:
                return r
            heapq.heappop(self._heap)
        return None

    def _choose_next(self) -> int | None:
        """Próxima fase = a que atende o topo da fila (None = segue o ciclo)."""
        top = self._top()
        return phase_for(self.signal.phases, top.movement) if top else None

    # ----------------------------------------------------------- controle
    def step(self, now: float) -> None:
        """Chamado pela thread controladora, dentro do Lock do cruzamento."""
        self._expire(now)
        sig = self.signal
        if self.preemption and sig.stage == "green" and not sig.preempted:
            top = self._top()
            if (
                top is not None
                and self._effective(top, now) >= config.PRIORITY_EMERGENCY
                and not sig.allows(*top.movement)
                and now - sig.green_start >= config.SIGNAL_MIN_GREEN
            ):
                target = phase_for(sig.phases, top.movement)
                if target is not None:
                    cut_name = sig.phase_name
                    sig.cut(now, target)
                    reason = "aging" if top.priority < config.PRIORITY_EMERGENCY else "emergência"
                    self._on_event(
                        "preempt",
                        f"🚨 preempção ({reason}): corta '{cut_name}' e abre "
                        f"'{sig.phases[target][0]}' para {top.label or top.vid}",
                    )
        sig.step(now, self._choose_next if self.uses_queue else None)

    def admit(self, vid: str, occupant_moves: dict, now: float) -> bool:
        """Chamado dentro do Lock do cruzamento. True = o veículo entra agora."""
        r = self.requests.get(vid)
        if r is None or not self.signal.allows(*r.movement):
            return False
        if any(movements_conflict(r.movement, m) for m in list(occupant_moves.values())):
            return False
        del self.requests[vid]
        return True

    def shift_time(self, dt: float) -> None:
        for r in self.requests.values():
            r.arrival += dt
            r.last_seen += dt
        self.signal.shift_time(dt)
        # as chaves do heap ficam todas deslocadas da mesma constante: ordem mantida

    def state(self, occupant_moves: dict, now: float) -> dict:
        return self.signal.state()

    def info(self) -> dict:
        return {
            "queue": len(self.requests),
            "preempted": self.signal.preempted,
            "phase": self.signal.phase_name,
        }


def make_controller(algorithm: str, now: float, preemption: bool = True,
                    aging: bool = True, on_event=None) -> SignalController:
    policy = algorithm if algorithm in ("fixed", "fcfs", "priority") else "fixed"
    return SignalController(now, policy, preemption, aging, on_event)
