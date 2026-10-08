# Roadmap — Sincronismo e Scheduling

Tela: `http://localhost:5173/scheduling` (sempre multithread: 1 thread por veículo
+ spawner, monitor de colisão e reaper).

## Feito (etapa 1 — sincronismo)

- [x] Rotas `/threads` (tela MULTI vs MONO original) e `/scheduling`.
- [x] Botão **Semáforo ON/OFF** que liga/desliga o sincronismo do cruzamento em tempo real
      (`POST /api/scheduling/sync`).
- [x] Semáforo realista em 6 fases (N/S reto+direita, N esquerda, S esquerda, L/O reto+direita,
      L esquerda, O esquerda; cada seta esquerda abre junto com a direita do eixo
      perpendicular, com amarelo e vermelho geral), avançado por uma thread controladora
- [x] Faixa exclusiva de conversão à esquerda antes de cada cruzamento
      (`backend/app/signals.py`). A leitura do sinal e a entrada ficam dentro do
      `threading.Lock` do cruzamento (`Intersection.try_enter_signal`).
- [x] Faixas por sentido (mão direita), fila na faixa, conversões à direita/esquerda
      com pisca, e colisão pela matriz de conflitos de movimentos.
- [x] Métricas separadas por fase ON / OFF (`backend/app/metrics_sched.py`).
- [x] Novos veículos com prioridade: ambulância 🚑, polícia 🚓, bombeiro 🚒
      (`SCHED_VEHICLE_TYPES` em `backend/app/config.py`, ~15% dos spawns).

## A fazer

### 1. Priority Scheduling (PS) ligado / desligado

- [ ] Botão **Prioridade ON/OFF** na tela `/scheduling`.
- [ ] Com PS ligado, veículo de emergência parado no vermelho **antecipa a fase** do
      seu movimento (preempção de semáforo): o `TrafficSignal` encurta o verde atual,
      passa por amarelo/vermelho geral e abre a fase da emergência.
      - Implementação sugerida: fila de pedidos por cruzamento (`heapq` de
        `(-priority, chegada, vehicle_id)`), lida pela thread controladora dentro do
        mesmo Lock do semáforo.
- [ ] Com PS desligado: ciclo fixo atual (`signals.PHASES`).
- [ ] PS só faz sentido com o semáforo ligado; decidir se o botão força o sync ON
      ou fica desabilitado quando o sync está OFF.
- [ ] Tratar **starvation**: veículos comuns podem esperar indefinidamente com muitas
      emergências. Mitigar com **aging** (prioridade efetiva sobe com o tempo de espera).

### 2. Outros algoritmos de scheduling

- [ ] Seletor de algoritmo na tela (substitui ou complementa o botão de PS):
  - [ ] **FCFS** (First Come, First Served) — fila por ordem de chegada no cruzamento.
  - [ ] **Round Robin** — alterna as direções (H/V) do cruzamento com um quantum
        de tempo (semáforo temporizado clássico).
  - [ ] **SJF** (Shortest Job First) — passa primeiro quem atravessa mais rápido
        (menor tempo de travessia = `2 * INTERSECTION_RADIUS / speed`).
  - [ ] **Priority** (com e sem preempção / aging).
- [ ] Métricas por algoritmo (mesma estrutura de baldes do `SchedMetrics`, trocando a
      chave `on`/`off` pelo nome do algoritmo).

### 3. Métricas de prioridade

- [ ] Tempo médio de viagem **emergência vs comum** com PS ligado vs desligado
      (a coleta por categoria já existe: `average_trip_time_emergency` /
      `average_trip_time_normal`).
- [ ] Tempo médio de espera no cruzamento por categoria (hoje é agregado).
- [ ] Tempo máximo de espera (para evidenciar starvation).
- [ ] Throughput: veículos finalizados por minuto.

### 4. Documentação

- [ ] Atualizar `docs/METRICAS.md` com as métricas de scheduling quando forem implementadas.
