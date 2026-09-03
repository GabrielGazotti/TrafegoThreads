# 🚗 Simulador de Trânsito — Versão SEM Sincronização

Simulador de trânsito concorrente em **Python + FastAPI + React**, construído
propositalmente **sem** mecanismos de sincronização (`Lock`,
`Condition`, `Event` de coordenação, filas globais etc.) para demonstrar,
de forma visual e mensurável, **Race Conditions**, colisões e
congestionamentos causados por Threads concorrentes.

```
React → WebSocket → FastAPI → SimulationManager → Threads
                                        ├── Thread "spawner"
                                        ├── Thread "monitor de colisão"
                                        ├── Thread "reaper"
                                        └── Thread "veículo" (1 por veículo) 🚗🚕🚌🏍️🚐
```

## Estrutura

```
traffic-sim/
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── config.py       # constantes da simulação (cidade, veículos, tempos)
│       ├── metrics.py      # contadores SEM lock (de propósito)
│       ├── city.py         # ruas e cruzamentos (try_enter/leave sem lock)
│       ├── vehicle.py      # Vehicle — tick independente; thread só no modo MULTI
│       ├── simulation.py   # modo MULTI (spawner, monitor, reaper + N threads)
│       ├── simulation_mono.py  # modo MONO (1 loop sequencial)
│       └── main.py         # FastAPI + WS /ws/simulation e /ws/simulation-mono
└── frontend/
    └── src/
        ├── hooks/useSimulationSocket.js
        ├── components/CityMap, ModeFrame, ThreadStrip, UtilizationPanel
        └── App.jsx         # tela split MULTI vs MONO (apresentação)
```

## Como rodar

### Backend

Linux / macOS:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # opcional
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Windows (PowerShell):

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Se o PowerShell bloquear o `Activate.ps1` com erro de política de execução, rode
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` antes, ou pule a
ativação e chame o interpretador do venv direto:
`.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`.

A API sobe em `http://localhost:8000`:
- `GET /api/config` — dimensões e ruas da cidade
- `GET /api/snapshot` / `GET /api/snapshot-mono` — snapshot pontual (debug)
- `POST /api/reset` — reinicia as duas simulações
- `WS /ws/simulation` — modo MULTI (1 thread por veículo)
- `WS /ws/simulation-mono` — modo MONO (loop sequencial)

### Apresentação (tela)

O frontend abre **duas cidades lado a lado** (MULTI quente / MONO frio), com:
- painel de utilizacao: **Threads**, **Ticks/s**, **Race** (duas threads acharam o cruzamento livre), **Veíc. env.**; badge **2+** no mapa quando ha concorrencia ao vivo
- grade de veiculos (MULTI paralelos / MONO 1 por vez com ▶)
- reset com mesma seed aleatoria para comparacao justa

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Acesse `http://localhost:5173`. Se o backend não estiver em `localhost:8000`,
defina `VITE_WS_URL` e `VITE_API_URL` num arquivo `.env` do frontend.

## Onde está a Race Condition?

O cruzamento é modelado em `backend/app/city.py`, classe `Intersection`.
O método `try_enter()` faz exatamente o padrão descrito no enunciado:

```python
was_free = len(self.occupants) == 0     # 1) verifica
time.sleep(random.uniform(0.0005, 0.006))  # 2) "processa" (aumenta a janela de corrida)
self.occupants.append(vehicle_id)        # 3) entra, sem checar de novo
self.occupied_by = vehicle_id
```

Como não existe nenhum `Lock` protegendo essas três etapas, duas ou mais
Threads (`Vehicle`) podem ler `occupants` vazio ao mesmo tempo e entrar
"simultaneamente" no cruzamento. Isso só conta como **Race** se o veículo
viu o cruzamento livre e, ao entrar, já havia outro — fila (um atrás do
outro) não entra nesse contador. O `monitor de colisão` pode transformar
a sobreposição em **colisão** se os veículos ficarem próximos demais.

Outros pontos deliberadamente inseguros:
- `Metrics` incrementa contadores com `x += 1` sem lock (perda de contagem sob carga).
- O dicionário global `SimulationManager.vehicles` é lido e escrito por várias
  Threads (spawner, monitor de colisão, reaper, e cada veículo se auto-removendo)
  ao mesmo tempo — por isso há `try/except` espalhados, não para "corrigir" a
  corrida, mas para a simulação não travar quando ela acontece.

## Métricas expostas

Número de veículos (criados/ativos/finalizados), Threads ativas
(`threading.active_count()`), colisões, conflitos de cruzamento, veículos
aguardando, tempo médio de espera, eventos processados e tempo de execução —
tudo em `GET /api/snapshot` e em cada frame do WebSocket.

## Preparado para a versão sincronizada

A arquitetura já isola os pontos que a versão com `Lock` vai alterar:

- `Intersection.try_enter()` / `Intersection.leave()` → ganham um
  `threading.Lock` por cruzamento.
- `Metrics` → ganha um `Lock` interno nos métodos `inc_*`.
- `SimulationManager.vehicles` → pode virar um dicionário protegido por Lock,
  ou continuar como está e usar apenas locks nos pontos de mutação.

Nenhuma dessas mudanças exige alterar `Vehicle`, `main.py` ou o frontend —
basta criar (por exemplo) `simulation_sync.py`, reaproveitando `City`,
`Vehicle` e `Metrics` com essas pequenas trocas, e apontar um novo endpoint
`/ws/simulation-sync` para comparação lado a lado.

## Importante

Esta é a versão **caótica, sem sincronização**, criada de propósito para
efeitos didáticos (ex.: disciplina de Sistemas Operacionais / Concorrência).
As "falhas" (conflitos, colisões, contadores imprecisos) são o resultado
esperado e **não devem ser corrigidas** nesta versão.
