import asyncio
import json
import random
from typing import Literal

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config
from .simulation import SimulationManager
from .simulation_mono import SimulationManagerMono
from .simulation_sched import SimulationManagerSched
from .vehicle import reset_id_counter
from .vehicle_sched import reset_sched_id_counter


class SyncToggle(BaseModel):
    enabled: bool


class ControlAction(BaseModel):
    action: Literal["start", "pause", "reset"]


app = FastAPI(title="Simulador de Trânsito — Threads e Scheduling")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sim_multi = SimulationManager()
sim_mono = SimulationManagerMono()
sim_sched = SimulationManagerSched()

# nenhuma simulação inicia sozinha: cada tela tem seu botão Iniciar.
# Quando a última conexão de uma tela fecha, a simulação dela é pausada.
_viewers = {"threads": 0, "scheduling": 0}


def _pause_group(group: str) -> None:
    if group == "threads":
        sim_multi.pause()
        sim_mono.pause()
    else:
        sim_sched.pause()


async def _stream(websocket: WebSocket, group: str, get_sim) -> None:
    await websocket.accept()
    _viewers[group] += 1
    try:
        while True:
            await websocket.send_text(json.dumps(get_sim().snapshot()))
            await asyncio.sleep(config.BROADCAST_INTERVAL)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _viewers[group] -= 1
        if _viewers[group] <= 0:
            _viewers[group] = 0
            _pause_group(group)


@app.on_event("shutdown")
async def on_shutdown():
    sim_multi.stop()
    sim_mono.stop()
    sim_sched.stop()


@app.get("/")
def root():
    return {
        "status": "ok",
        "modes": ["multi", "mono", "scheduling"],
        "websockets": ["/ws/simulation", "/ws/simulation-mono", "/ws/scheduling"],
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


@app.post("/api/threads/control")
def control_threads(body: ControlAction):
    if body.action == "reset":
        reset_simulation()
    elif body.action == "start":
        sim_multi.start()
        sim_mono.start()
    else:
        sim_multi.pause()
        sim_mono.pause()
    return {"status": sim_multi.status}


@app.get("/api/scheduling/config")
def get_scheduling_config():
    return {
        "city_width": config.SCHED_CITY_WIDTH,
        "city_height": config.SCHED_CITY_HEIGHT,
        "horizontal_streets": config.SCHED_HORIZONTAL_STREETS,
        "vertical_streets": config.SCHED_VERTICAL_STREETS,
        "intersection_radius": config.INTERSECTION_RADIUS,
        "road_width": config.SCHED_ROAD_WIDTH,
        "lane_offset": config.SCHED_LANE_OFFSET,
        "left_lane_offset": config.SCHED_LEFT_LANE_OFFSET,
        "left_pocket": config.SCHED_LEFT_POCKET,
        "vehicle_types": config.SCHED_VEHICLE_TYPES,
        "emergency_spawn_rate": config.SCHED_EMERGENCY_SPAWN_RATE,
        "priority_normal": config.PRIORITY_NORMAL,
        "priority_emergency": config.PRIORITY_EMERGENCY,
    }


@app.get("/api/scheduling/snapshot")
def get_scheduling_snapshot():
    return sim_sched.snapshot()


@app.post("/api/scheduling/sync")
def set_scheduling_sync(body: SyncToggle):
    sim_sched.set_sync(body.enabled)
    return {"sync_enabled": sim_sched.sync_enabled}


@app.post("/api/scheduling/reset")
def reset_scheduling():
    global sim_sched  # noqa: PLW0603
    sync_enabled = sim_sched.sync_enabled
    sim_sched.stop()
    reset_sched_id_counter()
    sim_sched = SimulationManagerSched(sync_enabled=sync_enabled)
    sim_sched.start()
    return {"status": "reiniciado", "sync_enabled": sync_enabled}


@app.post("/api/scheduling/control")
def control_scheduling(body: ControlAction):
    if body.action == "reset":
        reset_scheduling()
    elif body.action == "start":
        sim_sched.start()
    else:
        sim_sched.pause()
    return {"status": sim_sched.status}


@app.websocket("/ws/simulation")
async def websocket_simulation(websocket: WebSocket):
    await _stream(websocket, "threads", lambda: sim_multi)


@app.websocket("/ws/simulation-mono")
async def websocket_simulation_mono(websocket: WebSocket):
    await _stream(websocket, "threads", lambda: sim_mono)


@app.websocket("/ws/scheduling")
async def websocket_scheduling(websocket: WebSocket):
    await _stream(websocket, "scheduling", lambda: sim_sched)
