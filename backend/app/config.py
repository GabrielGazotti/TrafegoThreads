"""
Configurações globais da simulação.

Este módulo concentra todos os "números mágicos" da simulação para
facilitar ajustes e, futuramente, a criação da versão sincronizada
(basta importar as mesmas constantes em um novo `simulation_sync.py`).
"""

# --- Dimensões da cidade (em pixels lógicos, usados também pelo frontend) ---
CITY_WIDTH = 900
CITY_HEIGHT = 650

# Posições das ruas horizontais (eixo Y) e verticais (eixo X)
HORIZONTAL_STREETS = [100, 250, 400, 550]   # valores de Y
VERTICAL_STREETS = [120, 320, 520, 720]     # valores de X

# Raio (em pixels) da "zona de cruzamento" — quando um veículo entra
# nessa zona, ele precisa decidir se para ou avança.
INTERSECTION_RADIUS = 22

# Distância mínima entre dois veículos para não ser considerada colisão
COLLISION_DISTANCE = 14

# --- Geração contínua de veículos ---
SPAWN_INTERVAL_MIN = 0.35   # segundos
SPAWN_INTERVAL_MAX = 1.4
MAX_VEHICLES = 60           # limite de segurança (não é sincronização, é só um teto)


# --- Frequência de atualização ---
COLLISION_CHECK_INTERVAL = 0.12
BROADCAST_INTERVAL = 0.12   # taxa de envio de estado via WebSocket

# --- Tipos de veículo: (emoji, velocidade px/tick, intervalo de tick, agressividade) ---
# agressividade = probabilidade [0..1] de o veículo IGNORAR a ocupação
# do cruzamento e tentar atravessar mesmo assim -> aumenta o caos.
VEHICLE_TYPES = {
    "carro":    {"emoji": "🚗", "speed": 55,  "tick": 0.05, "aggressiveness": 0.12},
    "taxi":     {"emoji": "🚕", "speed": 80,  "tick": 0.04, "aggressiveness": 0.30},
    "onibus":   {"emoji": "🚌", "speed": 32,  "tick": 0.07, "aggressiveness": 0.05},
    "moto":     {"emoji": "🏍️", "speed": 95,  "tick": 0.03, "aggressiveness": 0.45},
    "van":      {"emoji": "🚐", "speed": 45,  "tick": 0.06, "aggressiveness": 0.18},
}

# Tempo (s) que um veículo "travado" (crashed) permanece visível antes de sumir
CRASH_LINGER_TIME = 3.0

# Tamanho máximo do log de eventos mantido em memória
EVENT_LOG_MAXLEN = 200
