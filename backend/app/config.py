CITY_WIDTH = 900
CITY_HEIGHT = 650

HORIZONTAL_STREETS = [100, 250, 400, 550]   # valores de Y
VERTICAL_STREETS = [120, 320, 520, 720]     # valores de X

INTERSECTION_RADIUS = 22

COLLISION_DISTANCE = 14

SPAWN_INTERVAL_MIN = 0.35
SPAWN_INTERVAL_MAX = 1.4
MAX_VEHICLES = 100


COLLISION_CHECK_INTERVAL = 0.12
BROADCAST_INTERVAL = 0.12
RACE_WINDOW_MIN = 0.04
RACE_WINDOW_MAX = 0.18

VEHICLE_TYPES = {
    "carro":    {"emoji": "🚗", "speed": 55,  "tick": 0.05, "aggressiveness": 0.12},
    "taxi":     {"emoji": "🚕", "speed": 80,  "tick": 0.04, "aggressiveness": 0.30},
    "onibus":   {"emoji": "🚌", "speed": 32,  "tick": 0.07, "aggressiveness": 0.05},
    "moto":     {"emoji": "🏍️", "speed": 95,  "tick": 0.03, "aggressiveness": 0.45},
    "van":      {"emoji": "🚐", "speed": 45,  "tick": 0.06, "aggressiveness": 0.18},
}

PRIORITY_NORMAL = 1
PRIORITY_EMERGENCY = 3

SCHED_VEHICLE_TYPES = {
    **{name: {**cfg, "priority": PRIORITY_NORMAL} for name, cfg in VEHICLE_TYPES.items()},
    "ambulancia": {"emoji": "🚑", "speed": 85, "tick": 0.04, "aggressiveness": 0.25,
                   "priority": PRIORITY_EMERGENCY},
    "policia":    {"emoji": "🚓", "speed": 90, "tick": 0.04, "aggressiveness": 0.30,
                   "priority": PRIORITY_EMERGENCY},
    "bombeiro":   {"emoji": "🚒", "speed": 60, "tick": 0.06, "aggressiveness": 0.20,
                   "priority": PRIORITY_EMERGENCY},
}

# fração dos veículos gerados que são de emergência (modo scheduling).
# Ajustável na tela até SCHED_EMERGENCY_RATE_MAX para evidenciar starvation.
SCHED_EMERGENCY_SPAWN_RATE = 0.15
SCHED_EMERGENCY_RATE_MAX = 0.8

# cidade da tela /scheduling: mais larga e com menos cruzamentos (2 x 3)
SCHED_CITY_WIDTH = 1500
SCHED_CITY_HEIGHT = 520
SCHED_HORIZONTAL_STREETS = [150, 370]
SCHED_VERTICAL_STREETS = [300, 750, 1200]
SCHED_MAX_VEHICLES = 45

# faixas e conversões (modo scheduling) — mão direita.
# Rua de 40 px: por sentido, faixa de dentro (conversão à esquerda) a 5 px do
# centro e faixa de fora (reto/direita) a 15 px.
SCHED_ROAD_WIDTH = 40
SCHED_LANE_OFFSET = 15
SCHED_LEFT_LANE_OFFSET = 5
SCHED_LEFT_POCKET = 90   # distância antes do cruzamento em que a faixa da esquerda existe
SCHED_FOLLOW_GAP = 20
SCHED_TURN_PROBS = {"straight": 0.6, "right": 0.2, "left": 0.2}
SCHED_MAX_TURNS = 2

# ciclo do semáforo (segundos) — todos os cruzamentos na mesma fase.
# O verde do reto é longo o bastante para o carro chegar ao próximo cruzamento
# ainda aberto (450 px entre ruas verticais / ~60 px/s).
SIGNAL_GREEN_THROUGH = 8.0
SIGNAL_GREEN_LEFT = 2.5
SIGNAL_YELLOW = 0.8
SIGNAL_ALL_RED = 1.0
SIGNAL_CONTROLLER_INTERVAL = 0.05

# ---------------------------------------------------------------- scheduling
# Algoritmos de escalonamento do cruzamento (só valem com o semáforo ligado).
SCHED_ALGORITHMS = {
    "fixed":    "Ciclo fixo",
    "priority": "Prioridade",
    "fcfs":     "FCFS",
}
SCHED_DEFAULT_ALGORITHM = "fixed"

# Priority Scheduling
# verde mínimo antes de uma preempção poder cortar a fase (evita "pisca-pisca")
SIGNAL_MIN_GREEN = 1.5
# aging: prioridade efetiva = prioridade + espera (s) * SCHED_AGING_RATE.
# Com 0.1, um veículo comum (1) alcança a emergência (3) depois de 20 s parado.
SCHED_AGING_RATE = 0.1

# pedido de passagem sem renovação há mais que isso é descartado
# (veículo saiu do cruzamento por outro caminho, colidiu, semáforo trocou etc.)
SCHED_REQUEST_TTL = 1.0

# modo comparação: simulações rodando ao mesmo tempo, mesma seed (mesmo fluxo de veículos)
# "off" = semáforo desligado; os demais são chaves de SCHED_ALGORITHMS
SCHED_COMPARE_LANES = ["off", "fixed", "priority", "fcfs"]
SCHED_COMPARE_DEFAULT = ["fixed", "priority", "fcfs"]
# antes disso a vazão (veíc/min) é só ruído e não é exibida
SCHED_MIN_ELAPSED_FOR_RATE = 10.0

CRASH_LINGER_TIME = 3.0

EVENT_LOG_MAXLEN = 200
