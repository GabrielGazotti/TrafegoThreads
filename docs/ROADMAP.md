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

## Feito (etapa 2 — scheduling)

Escalonadores em `backend/app/scheduler.py`, um controlador por cruzamento, acessado
sempre dentro do Lock do cruzamento (`Intersection.try_enter_sched`).

### 1. Priority Scheduling (PS) ligado / desligado

- [x] Seletor **Escalonador** na tela `/scheduling`: "Ciclo fixo" = PS desligado,
      "Prioridade" = PS ligado (o seletor substituiu o botão Prioridade ON/OFF).
- [x] Preempção de semáforo: o topo da fila de prioridade, no vermelho e com prioridade
      efetiva de emergência, corta o verde atual (após `SIGNAL_MIN_GREEN`), passa por
      amarelo/vermelho geral e abre a fase dele (`TrafficSignal.cut`).
      - Fila de pedidos por cruzamento em `heapq`, lida pela thread controladora
        dentro do mesmo Lock do semáforo.
- [x] PS desligado: ciclo fixo (`signals.PHASES`).
- [x] Com o semáforo OFF o seletor fica **desabilitado** (sem escalonamento).
- [x] Starvation: **aging** com prioridade efetiva = prioridade + espera × `SCHED_AGING_RATE`
      (chave do heap invariante no tempo). Botões Preempção ON/OFF e Aging ON/OFF.
- [x] Slider **🚑 Emergências** (0–80% dos spawns) para provocar starvation na demonstração.

### 2. Outros algoritmos de scheduling

- [x] **FCFS**: abre a fase de quem chegou primeiro (mesmo semáforo de 6 fases).
- [x] **Priority** com e sem preempção, com e sem aging.
- [x] Round Robin e SJF foram implementados e depois **removidos** (fora do escopo da
      apresentação).
- [x] Métricas por algoritmo: baldes do `SchedMetrics` com chave `off` ou nome do algoritmo.

### 2b. Modo comparação

- [x] Aba **Comparação** na tela `/scheduling`: de 2 a 4 modos (OFF, Ciclo fixo,
      Prioridade, FCFS) rodando ao mesmo tempo, com a mesma seed (mesmo fluxo de
      veículos) — `backend/app/simulation_compare.py`.
- [x] Barras de destaque por métrica, um mapa por modo, tabela comparativa.
- [x] Aba **Individual** mantida (uma simulação, semáforo/escalonador ao vivo).

### 3. Métricas de prioridade

- [x] Viagem média emergência × comum por modo.
- [x] Espera média no cruzamento por categoria.
- [x] Espera máxima por categoria (evidencia starvation).
- [x] Throughput (veículos finalizados por minuto) e número de preempções.

### 4. Documentação

- [x] `docs/METRICAS.md` atualizado com as métricas e os algoritmos.

## Ideias para depois

- [ ] Exportar o comparativo por modo (CSV) para usar nos slides.
- [ ] Benchmark automático: rodar a comparação por um tempo fixo e salvar o resultado.
