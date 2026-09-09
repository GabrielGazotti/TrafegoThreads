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

CRASH_LINGER_TIME = 3.0

EVENT_LOG_MAXLEN = 200
