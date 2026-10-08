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

## Tela `/scheduling` (sincronismo)

Fonte: `backend/app/metrics_sched.py`. Aqui os contadores **têm Lock**: o experimento
é o cruzamento, não os contadores, então a medição precisa ser confiável.

As métricas são guardadas em dois **baldes**, `off` e `on`. Todo evento é contado no
balde da fase em que o semáforo estava **no momento do evento**. Trocar o semáforo
não zera nada; o reset da tela zera os dois baldes.

| Métrica | Como é calculada | Por quê |
|---|---|---|
| Colisões | Dois ou mais veículos no mesmo cruzamento, a menos de `COLLISION_DISTANCE`, **e com movimentos em conflito** (matriz de conflitos, ver abaixo). Quem vem de frente na outra faixa não conta. | Mostra o efeito do sincronismo: com semáforo ON só entram juntos movimentos compatíveis, então deve ficar ~0. |
| Colisões / min | `colisões / (tempo na fase em minutos)`. | As fases ON e OFF podem durar tempos diferentes; a taxa permite comparar de forma justa. |
| Veículos envolvidos | Soma dos veículos nos grupos de colisão. | Tamanho do estrago de cada colisão. |
| Race conditions | Mesmo critério da tela `/threads` (só existe com semáforo OFF); com semáforo ON a leitura do sinal e a entrada ficam dentro do Lock, então não ocorre. | Evidencia a causa das colisões. |
| Espera média no cruzamento (s) | Para **cada entrada em cruzamento**, soma o tempo que o veículo ficou parado desde o cruzamento anterior (sinal vermelho, fila atrás de outro veículo, hesitação) e tira a média. Entradas sem espera contam como 0. | Custo do sincronismo: menos colisões em troca de mais espera. |
| Viagem média — emergência / comum (s) | Tempo do spawn até sair da cidade, separado pela prioridade do veículo (`priority >= PRIORITY_EMERGENCY`). Contado na fase em que o veículo **termina**. | Base para comparar Priority Scheduling ligado/desligado na próxima etapa. |
| Veículos finalizados | Veículos que saíram da cidade na fase. | Throughput. |
| Tempo na fase (s) | Tempo acumulado com o semáforo naquele estado. | Normaliza as demais métricas. |

### Faixas e manobras

- Cada rua tem um sentido por lado (mão direita). Por sentido: faixa de fora
  (reto/direita, `SCHED_LANE_OFFSET`) e, nos `SCHED_LEFT_POCKET` px antes de cada
  cruzamento, uma **faixa exclusiva de conversão à esquerda** (`SCHED_LEFT_LANE_OFFSET`).
  Quem vai virar à esquerda muda para ela e espera a seta sem travar quem vai reto.
- Veículos fazem fila atrás de quem está na frente na mesma faixa (`SCHED_FOLLOW_GAP`).
- Em cada cruzamento o veículo escolhe uma manobra: reto (60%), direita (20%) ou
  esquerda (20%), no máximo `SCHED_MAX_TURNS` conversões. O pisca aparece no mapa.

### Como o semáforo funciona

Cada cruzamento tem um `TrafficSignal` (`backend/app/signals.py`) com o ciclo:

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
Uma thread **controladora de semáforos** avança as fases de todos os cruzamentos,
sempre dentro do `threading.Lock` de cada cruzamento.

`Intersection.try_enter_signal()` (`backend/app/city.py`):

1. Tenta pegar o mesmo `Lock` **sem bloquear**.
2. Dentro do Lock: se o sinal do movimento do veículo (lado de chegada + manobra)
   não estiver verde, devolve `False`; senão entra.
3. Solta o Lock.

O veículo que recebe `False` fica parado e tenta de novo no próximo tick
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

Nesta etapa a prioridade só é exibida e medida; ela ainda **não** altera a ordem de
entrada no cruzamento (ver `docs/ROADMAP.md`).
