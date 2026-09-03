"""
API FastAPI + WebSocket do Simulador de Trânsito.

Dois modos em paralelo:
  /ws/simulation      -> MULTI (1 thread por veículo)
  /ws/simulation-mono -> MONO (loop sequencial)
"""

import asyncio
import json
import random

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .simulation import SimulationManager
from .simulation_mono import SimulationManagerMono
from .vehicle import reset_id_counter

app = FastAPI(title="Simulador de Trânsito — MULTI vs MONO")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sim_multi = SimulationManager()
sim_mono = SimulationManagerMono()


@app.on_event("startup")
async def on_startup():
    sim_multi.start()
    sim_mono.start()


@app.on_event("shutdown")
async def on_shutdown():
    sim_multi.stop()
    sim_mono.stop()


@app.get("/")
def root():
    return {
        "status": "ok",
        "modes": ["multi", "mono"],
        "websockets": ["/ws/simulation", "/ws/simulation-mono"],
    }


@app.get("/api/config")
def get_config():
    return {
        "city_width": config.CITY_WIDTH,
        "city_height": config.CITY_HEIGHT,
        "horizontal_streets": config.HORIZONTAL_STREETS,
        "vertical_streets": config.VERTICAL_STREETS,
        "intersection_radius": config.INTERSECTION_RADIUS,
        "vehicle_types": config.VEHICLE_TYPES,
    }


@app.get("/api/snapshot")
def get_snapshot():
    return sim_multi.snapshot()


@app.get("/api/snapshot-mono")
def get_snapshot_mono():
    return sim_mono.snapshot()


@app.post("/api/reset")
def reset_simulation():
    global sim_multi, sim_mono  # noqa: PLW0603
    sim_multi.stop()
    sim_mono.stop()

    seed = random.randint(0, 2**31 - 1)
    reset_id_counter()

    random.seed(seed)
    sim_multi = SimulationManager()
    sim_multi.start()

    random.seed(seed)
    sim_mono = SimulationManagerMono()
    sim_mono.start()

    return {"status": "reiniciado", "seed": seed}


@app.websocket("/ws/simulation")
async def websocket_simulation(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = sim_multi.snapshot()
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(config.BROADCAST_INTERVAL)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@app.websocket("/ws/simulation-mono")
async def websocket_simulation_mono(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = sim_mono.snapshot()
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(config.BROADCAST_INTERVAL)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
