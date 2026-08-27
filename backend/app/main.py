"""
API FastAPI + WebSocket do Simulador de Trânsito (versão SEM sincronização).

    React → WebSocket → FastAPI → SimulationManager → Threads (veículos)

Cada cliente conectado em /ws/simulation recebe, a cada
`config.BROADCAST_INTERVAL` segundos, um snapshot JSON com veículos,
cruzamentos, métricas, nível de caos e eventos recentes.
"""

import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .simulation import SimulationManager

app = FastAPI(title="Simulador de Trânsito — SEM Sincronização")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sim = SimulationManager()


@app.on_event("startup")
async def on_startup():
    sim.start()


@app.on_event("shutdown")
async def on_shutdown():
    sim.stop()


@app.get("/")
def root():
    return {
        "status": "ok",
        "mode": "sem-sincronizacao",
        "mensagem": "Use o WebSocket em /ws/simulation para ver a simulação em tempo real.",
    }


@app.get("/api/config")
def get_config():
    """Envia ao frontend as dimensões/posições da cidade para desenhar o mapa."""
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
    """Snapshot pontual via HTTP (útil para debug fora do WebSocket)."""
    return sim.snapshot()


@app.post("/api/reset")
def reset_simulation():
    global sim  # noqa: PLW0603
    sim.stop()
    sim = SimulationManager()
    sim.start()
    return {"status": "reiniciado"}


@app.websocket("/ws/simulation")
async def websocket_simulation(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = sim.snapshot()
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(config.BROADCAST_INTERVAL)
    except WebSocketDisconnect:
        pass
    except Exception:
        # Não deixamos uma exceção de serialização (possível durante uma
        # mutação concorrente do estado) derrubar o servidor inteiro.
        pass
