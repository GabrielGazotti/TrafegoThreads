# Métricas utilizadas

## Tela `/threads` (MULTI vs MONO)

Fonte: `backend/app/metrics.py` (contadores **sem lock**, de propósito — podem
perder contagem sob carga, o que também faz parte da demonstração).

| Métrica | Como é calculada |
|---|---|
| Threads ativas | `3 + veículos vivos` no MULTI (spawner, monitor, reaper + 1 por veículo); sempre 1 no MONO. |
| Pico de threads | Maior valor de threads ativas já observado. |
| Ticks/s (Vel. média) | Total de ticks de veículos / tempo de execução. |
| Race conditions (`intersection_conflicts`) | Veículo leu o cruzamento **livre**, mas ao entrar já havia outro — duas threads passaram pela mesma janela do check-then-act (`Intersection.try_enter`). Fila não conta. |
| Colisões | Grupos de 2+ veículos no **mesmo cruzamento** a menos de `COLLISION_DISTANCE` (`backend/app/collisions.py`). Cada grupo = 1 colisão. |
| Veículos envolvidos | Soma dos veículos de todos os grupos de colisão. |

## Tela `/scheduling` (sincronismo e scheduling)

Fonte: `backend/app/metrics_sched.py`. Aqui os contadores **têm Lock**: o experimento
é o cruzamento, não os contadores, então a medição precisa ser confiável.

As métricas são guardadas em **baldes**, um por modo de controle do cruzamento:

| Balde | Quando |
|---|---|
| `off` | Semáforo desligado (sem sincronismo). |
| `fixed` | Semáforo ligado, ciclo fixo de 6 fases (Priority Scheduling desligado). |
| `priority`, `priority+aging`, `priority-np`, `priority-np+aging` | Prioridade; `-np` = não preemptiva, `+aging` = com aging. |
| `fcfs` | FCFS (ordem de chegada). |

Todo evento é contado no balde do modo ativo **no momento do evento**. Os baldes são
criados na primeira vez que o modo é usado. Trocar de modo não zera nada; o reset
da tela zera tudo. A tabela "Comparativo por modo" mostra uma coluna por balde
(a coluna do modo atual fica marcada com ●), com o melhor valor de cada linha em
verde e o pior em vermelho.

Médias e máximos **sem nenhuma amostra** aparecem como "—" (o backend manda `null`),
para não confundir "sem dados" com "zero". A vazão só aparece depois de
`SCHED_MIN_ELAPSED_FOR_RATE` (10 s) no modo — antes disso é só ruído.

## Modo comparação (recomendado para a apresentação)

Fonte: `backend/app/simulation_compare.py`. Na tela `/scheduling`, aba **Comparação**:
várias simulações rodam **ao mesmo tempo**, uma por modo (Semáforo OFF, Ciclo fixo,
Prioridade, FCFS — escolha de 2 a 4), cada uma com sua cidade e suas threads.

- Todas usam a **mesma seed**: o spawner sorteia tipo, intervalo e uma seed por
  veículo; cada veículo sorteia velocidade, rua, sentido e manobras com o próprio
  gerador (`SchedVehicle.rng`). Resultado: as simulações recebem **o mesmo fluxo de
  veículos**, e só o escalonador muda. (A hesitação do modo OFF usa o `random`
  global de propósito, porque depende do timing das threads.)
- Todas começam juntas e pausam juntas, então o **tempo de execução é igual**.
- Trocar os modos, a preempção ou o aging recomeça a comparação com uma seed nova;
  o slider de emergências vale para todas na hora, sem recomeçar.
- Medido: 4 simulações em paralelo mantêm ~22 ticks/s por veículo, o mesmo que 1 sozinha.

Na tela: barras de destaque por métrica (★ = melhor), um mapa por modo com os
principais números, e a tabela comparativa completa.

| Métrica | Como é calculada | Por quê |
|---|---|---|
| Colisões | Dois ou mais veículos no mesmo cruzamento, a menos de `COLLISION_DISTANCE`, **e com movimentos em conflito** (matriz de conflitos, ver abaixo). Quem vem de frente na outra faixa não conta. | Mostra o efeito do sincronismo: com o semáforo ligado só entram juntos movimentos compatíveis, então fica em 0 em todos os algoritmos. |
| Colisões / min | `colisões / (tempo no modo em minutos)`. | Os modos podem durar tempos diferentes; a taxa permite comparar de forma justa. |
| Veículos envolvidos | Soma dos veículos nos grupos de colisão. | Tamanho do estrago de cada colisão. |
| Race conditions | Mesmo critério da tela `/threads` (só existe com semáforo OFF); com o semáforo ligado, o pedido de vez e a entrada ficam dentro do Lock, então não ocorre. | Evidencia a causa das colisões. |
| Vazão (veíc/min) | `veículos finalizados / (tempo no modo em minutos)`. | Throughput: quantos veículos o escalonador consegue escoar. |
| Espera média (s) | Para **cada entrada em cruzamento**, soma o tempo que o veículo ficou parado desde o cruzamento anterior (sinal vermelho, fila atrás de outro veículo, hesitação) e tira a média. Entradas sem espera contam como 0. | Custo do sincronismo: menos colisões em troca de mais espera. |
| Espera média — emergência / comum (s) | Mesma amostra, separada pela prioridade do veículo (`priority >= PRIORITY_EMERGENCY`). | Mostra quem o algoritmo favorece. Com Prioridade, a emergência espera bem menos que o comum. |
| Espera máx. — emergência / comum (s) | Maior amostra de espera do modo, por categoria. | Evidencia **starvation**: sem aging e com muitas emergências, a espera máxima do comum dispara. |
| Viagem média — emergência / comum (s) | Tempo do spawn até sair da cidade, por categoria. Contado no modo em que o veículo **termina**. | Efeito de ponta a ponta do Priority Scheduling. |
| Preempções do semáforo | Quantas vezes um verde foi cortado para atender um pedido prioritário (só no modo Prioridade preemptiva). | Custo da preempção: cada corte gasta amarelo + vermelho geral. |
| Veículos finalizados | Veículos que saíram da cidade no modo. | Base da vazão. |
| Tempo no modo (s) | Tempo acumulado naquele modo (pausa não conta). | Normaliza as demais métricas. |

> Dica para a apresentação: use a aba **Comparação** e deixe rodar pelo menos 1–2
> minutos antes de comentar os números. Para mostrar starvation, suba
> **🚑 Emergências** para 50% ou mais e compare Prioridade com e sem aging
> (linha "Espera máx. — comum").

### Faixas e manobras

- Cada rua tem um sentido por lado (mão direita). Por sentido: faixa de fora
  (reto/direita, `SCHED_LANE_OFFSET`) e, nos `SCHED_LEFT_POCKET` px antes de cada
  cruzamento, uma **faixa exclusiva de conversão à esquerda** (`SCHED_LEFT_LANE_OFFSET`).
  Quem vai virar à esquerda muda para ela e espera a seta sem travar quem vai reto.
- Veículos fazem fila atrás de quem está na frente na mesma faixa (`SCHED_FOLLOW_GAP`).
- Em cada cruzamento o veículo escolhe uma manobra: reto (60%), direita (20%) ou
  esquerda (20%), no máximo `SCHED_MAX_TURNS` conversões. O pisca aparece no mapa.

### Como o semáforo funciona

Com o semáforo ligado (base dos três algoritmos), cada cruzamento tem um
`TrafficSignal` (`backend/app/signals.py`) com o ciclo:

1. N/S reto + direita
2. N esquerda + L/O direita
3. S esquerda + L/O direita
4. L/O reto + direita
5. L esquerda + N/S direita
6. O esquerda + N/S direita

A seta da esquerda abre **um lado por vez** (verde mais curto que o do reto), para
quem converte nunca cruzar com quem vem de frente. Cada sinal tem 3 luzes:
seta esquerda, reto e seta direita.

Entre as fases: amarelo (ninguém novo entra) e vermelho geral (limpa o cruzamento).
Todos os cruzamentos ficam **na mesma fase** (onda verde): quem passa no verde
encontra o próximo cruzamento do mesmo eixo também aberto.
Uma thread **controladora de semáforos** avança os controladores de todos os
cruzamentos, sempre dentro do `threading.Lock` de cada cruzamento. Ao ligar o semáforo
ou trocar de algoritmo, todos os cruzamentos recebem um controlador novo com o mesmo
instante de início (por isso a onda verde se mantém).

A entrada no cruzamento é feita por `Intersection.try_enter_sched()`; o passo a passo
está em [Algoritmos de scheduling](#algoritmos-de-scheduling). O veículo que recebe `False` fica parado e tenta de novo no próximo tick
(polling). Por isso dá para desligar o semáforo a qualquer momento sem deixar
thread presa em `acquire()`.

### Matriz de conflitos

`movements_conflict()` em `backend/app/signals.py`. Dois movimentos (lado de chegada, manobra):

- mesmo lado de chegada → não conflitam (é fila);
- mesma faixa de saída → conflitam (convergência);
- se um deles é conversão à direita → não conflitam;
- lados opostos: só reto x reto não conflita (faixas separadas); qualquer conversão à
  esquerda cruza quem vem de frente;
- lados perpendiculares → conflitam (cruzamento).

As fases do semáforo só liberam juntos movimentos que não conflitam.

### Prioridades dos veículos

| Tipo | Emoji | Prioridade |
|---|---|---|
| carro, táxi, ônibus, moto, van | 🚗 🚕 🚌 🏍️ 🚐 | `PRIORITY_NORMAL` (1) |
| ambulância, polícia, bombeiro | 🚑 🚓 🚒 | `PRIORITY_EMERGENCY` (3) |

A fração de emergências nos spawns começa em `SCHED_EMERGENCY_SPAWN_RATE` (15%) e
pode ser ajustada na tela (slider **🚑 Emergências**, até `SCHED_EMERGENCY_RATE_MAX`).
A prioridade só muda a ordem de entrada no algoritmo **Prioridade**.

## Algoritmos de scheduling

Fonte: `backend/app/scheduler.py`. Analogia com escalonamento de CPU:

| CPU | Cruzamento |
|---|---|
| Processador | O **verde**: uma fase do semáforo roda por vez |
| Processos na fila de prontos | Veículos parados na linha de retenção |
| Troca de contexto | Amarelo + vermelho geral entre as fases |
| Escalonador | Política que escolhe a **próxima fase** |

Os três algoritmos usam **o mesmo semáforo de 6 fases** (`signals.PHASES`); só muda
a política que escolhe a próxima fase. Assim a comparação mede a política, e não
um modelo de cruzamento diferente.

Fluxo de entrada (`Intersection.try_enter_sched()` em `backend/app/city.py`):

1. Tenta pegar o Lock do cruzamento **sem bloquear** (se estiver ocupado, tenta no próximo tick).
2. Registra ou renova o **pedido de passagem**: movimento, prioridade e instante de chegada.
3. Entra se o sinal do seu movimento estiver verde **e** ninguém dentro do cruzamento
   tiver movimento conflitante (matriz de conflitos, acima). Se entrar, o pedido sai da fila.
4. Solta o Lock.

Só o primeiro veículo de cada faixa chega à linha de retenção, então a fila tem no
máximo um pedido por faixa. Pedidos não renovados há mais de `SCHED_REQUEST_TTL`
são descartados.

| Algoritmo | Escolha da próxima fase | Preemptivo? | Ponto forte / fraco |
|---|---|---|---|
| **Ciclo fixo** (`fixed`) | Sempre a seguinte no ciclo, tenha ou não alguém esperando. | Não | Simples e previsível; desperdiça verde em faixa vazia. É o "Priority Scheduling desligado". |
| **FCFS** (`fcfs`) | A fase de quem está **há mais tempo** na fila (heap por chegada). Fila vazia: segue o ciclo. | Não | Justo: menor espera máxima. Emergência espera como qualquer um. |
| **Prioridade** (`priority`) | A fase do pedido **mais prioritário** (heap por prioridade). Fila vazia: segue o ciclo. | Opcional | Emergência passa primeiro; sem aging, os comuns podem sofrer starvation. |

Resultado típico (comparação de 2 min, mesma seed): o Ciclo fixo tem as maiores
esperas; a Prioridade tem a menor espera e a menor viagem das **emergências**; o FCFS
tem a menor espera e a menor espera máxima dos **comuns**. É o trade-off clássico
entre prioridade e justiça.

### Prioridade, preempção e aging

- Prioridade base: comum = 1, emergência = 3 (`PRIORITY_NORMAL` / `PRIORITY_EMERGENCY`).
- **Preemptiva:** se o topo da fila tem prioridade efetiva de emergência e está no
  vermelho, o controlador corta o verde atual (depois de `SIGNAL_MIN_GREEN`), passa
  por amarelo e vermelho geral e abre a fase dele (`TrafficSignal.cut`).
  **Não preemptiva:** nunca corta, só escolhe a próxima fase.
- **Aging:** prioridade efetiva = `prioridade + espera (s) * SCHED_AGING_RATE`. Com a taxa
  0.1, um veículo comum chega à prioridade de emergência depois de 20 s parado e passa
  a disputar a vez (e a preempção) de igual para igual.
- O heap guarda a chave `chegada * SCHED_AGING_RATE - prioridade` (com aging),
  `-prioridade` (sem aging) ou `chegada` (FCFS). Ordenar pela prioridade efetiva é
  equivalente a ordenar pela chave com aging, porque o termo `agora * taxa` é igual
  para todos. Por isso a chave não muda com o tempo e cabe num `heapq`. Pedidos que
  já saíram ficam no heap e são descartados quando chegam ao topo (remoção preguiçosa).
- No mapa, o anel amarelo tracejado em volta do cruzamento indica que a fase atual
  foi aberta por preempção. Cada preempção também vai para o log de eventos.
