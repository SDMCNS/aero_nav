"""
FastAPI application for the Aviation Navaid & Cockpit Avionics Simulator.
Provides REST APIs for airspace GeoJSON, airport metadata, and scenarios,
as well as a high-frequency WebSocket for real-time telemetry and avionics bus streaming.
"""

import asyncio
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from navaid_sim.database.loader import AirspaceDatabase
from navaid_sim.scenarios.runner import ScenarioRunner
from navaid_sim.scenarios.definitions import ALL_SCENARIOS


app = FastAPI(
    title="Aviation Navaid & Cockpit Avionics Simulator",
    version="3.0.0",
    description="High-fidelity simulation of radio navigation aids (VOR, DME, NDB, ILS, GNSS) in the Irish FIR(s).",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global simulation instances
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
db = AirspaceDatabase(ROOT_DIR)
runner = ScenarioRunner(db)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()


# Background simulation loop task
sim_task: Optional[asyncio.Task] = None

async def simulation_loop():
    while True:
        try:
            if runner.is_running:
                runner.step(dt_real_sec=0.1)
                # Broadcast at 10 Hz
                if manager.active_connections:
                    snapshot = runner.get_snapshot()
                    await manager.broadcast(snapshot)
            await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            await asyncio.sleep(0.1)


@app.on_event("startup")
async def startup_event():
    global sim_task
    sim_task = asyncio.create_task(simulation_loop())


@app.on_event("shutdown")
async def shutdown_event():
    global sim_task
    if sim_task:
        sim_task.cancel()


# Request Models
class SimControlRequest(BaseModel):
    action: str  # "play", "pause", "reset", "step", "set_speed", "seek"
    speed: Optional[float] = None
    fraction: Optional[float] = None


class TuneRequest(BaseModel):
    receiver: str  # "nav1", "nav2", "dme1", "adf1"
    station_id: str
    obs_deg: Optional[float] = None


class AircraftManualControl(BaseModel):
    heading_deg: Optional[float] = None
    altitude_ft: Optional[float] = None
    groundspeed_kts: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


# REST Endpoints
@app.get("/api/database/geojson")
async def get_airspace_geojson():
    """Returns FIR boundaries, navaids, airports, and waypoints as GeoJSON."""
    return db.to_geojson()


@app.get("/api/database/airports")
async def get_airports():
    """Returns detailed aerodrome physical and radio characteristics."""
    result = {}
    for ident, ap in db.airports.items():
        result[ident] = {
            "identifier": ap.identifier,
            "name": ap.name,
            "arp_lat": ap.arp_lat,
            "arp_lon": ap.arp_lon,
            "elevation_ft": ap.elevation_ft,
            "magnetic_variation": ap.magnetic_variation,
            "mag_var_deg": ap.mag_var_deg,
            "comms": ap.comms,
            "runways": [
                {
                    "designation": r.designation,
                    "true_bearing_deg": r.true_bearing_deg,
                    "magnetic_bearing_deg": r.magnetic_bearing_deg,
                    "dimensions_m": r.dimensions_m,
                    "thr_lat": r.thr_lat,
                    "thr_lon": r.thr_lon,
                    "thr_elevation_ft": r.thr_elevation_ft,
                    "ils_loc_id": r.ils_loc_id,
                    "ils_loc_freq": r.ils_loc_freq,
                    "ils_gp_freq": r.ils_gp_freq,
                }
                for r in ap.runways
            ],
        }
    return result


@app.get("/api/database/navaids")
async def get_navaids():
    """Returns complete list of navigation aids with frequencies and DOC."""
    result = []
    for key, n in db.navaids.items():
        result.append({
            "key": key,
            "id": n.id,
            "name": n.name,
            "type": n.type,
            "frequency": n.frequency,
            "freq_mhz": n.freq_mhz,
            "lat": n.lat,
            "lon": n.lon,
            "elevation_ft": n.elevation_ft,
            "channel": n.channel,
            "declination": n.declination,
            "doc_range_nm": n.doc_range_nm,
            "associated_airport": n.associated_airport,
            "runway_id": n.runway_id,
            "remarks": n.remarks,
            "restrictions": n.restrictions,
        })
    return result


@app.get("/api/scenarios")
async def get_scenarios():
    """Returns the list of 3 pre-configured scenarios."""
    scenarios_list = []
    for sc_id, sc in ALL_SCENARIOS.items():
        scenarios_list.append({
            "id": sc.id,
            "title": sc.title,
            "aircraft_type": sc.aircraft_type,
            "callsign": sc.callsign,
            "summary": sc.summary,
            "flight_level": sc.flight_level,
            "departure": sc.departure,
            "destination": sc.destination,
            "airspace_context": sc.airspace_context,
            "avionics_focus": sc.avionics_focus,
            "initial_alt_ft": sc.initial_alt_ft,
            "initial_speed_kts": sc.initial_speed_kts,
            "waypoints_count": len(sc.waypoints),
        })
    return scenarios_list


@app.get("/api/scenarios/{scenario_id}")
async def get_scenario_detail(scenario_id: str):
    if scenario_id not in ALL_SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")
    sc = ALL_SCENARIOS[scenario_id]
    return {
        "id": sc.id,
        "title": sc.title,
        "aircraft_type": sc.aircraft_type,
        "callsign": sc.callsign,
        "summary": sc.summary,
        "flight_level": sc.flight_level,
        "departure": sc.departure,
        "destination": sc.destination,
        "airspace_context": sc.airspace_context,
        "avionics_focus": sc.avionics_focus,
        "initial_alt_ft": sc.initial_alt_ft,
        "initial_speed_kts": sc.initial_speed_kts,
        "waypoints": [w.__dict__ for w in sc.waypoints],
    }


@app.post("/api/scenarios/{scenario_id}/select")
async def select_scenario(scenario_id: str):
    if scenario_id not in ALL_SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")
    runner.load_scenario(scenario_id)
    snapshot = runner.get_snapshot()
    await manager.broadcast(snapshot)
    return snapshot


@app.post("/api/simulation/control")
async def control_simulation(req: SimControlRequest):
    if req.action == "play":
        runner.play()
    elif req.action == "pause":
        runner.pause()
    elif req.action == "reset":
        runner.reset()
    elif req.action == "step":
        runner.step(dt_real_sec=0.5)
    elif req.action == "set_speed" and req.speed is not None:
        runner.set_speed_multiplier(req.speed)
    elif req.action == "seek" and req.fraction is not None:
        runner.seek_fraction(req.fraction)

    snapshot = runner.get_snapshot()
    await manager.broadcast(snapshot)
    return snapshot


@app.post("/api/avionics/tune")
async def tune_avionics(req: TuneRequest):
    runner.manual_tune(req.receiver, req.station_id, req.obs_deg)
    snapshot = runner.get_snapshot()
    await manager.broadcast(snapshot)
    return snapshot


@app.post("/api/aircraft/manual")
async def manual_aircraft_control(req: AircraftManualControl):
    if req.heading_deg is not None:
        runner.aircraft.true_heading_deg = req.heading_deg % 360.0
        runner.aircraft.update_magnetic_heading()
    if req.altitude_ft is not None:
        runner.aircraft.altitude_ft = max(0.0, req.altitude_ft)
    if req.groundspeed_kts is not None:
        runner.aircraft.groundspeed_kts = max(0.0, req.groundspeed_kts)
        runner.aircraft.true_airspeed_kts = runner.aircraft.groundspeed_kts
    if req.lat is not None and req.lon is not None:
        runner.aircraft.lat = req.lat
        runner.aircraft.lon = req.lon

    snapshot = runner.get_snapshot()
    await manager.broadcast(snapshot)
    return snapshot


@app.get("/api/simulation/state")
async def get_simulation_state():
    return runner.get_snapshot()


# WebSocket streaming endpoint
@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await manager.connect(websocket)
    # Send initial state
    await websocket.send_json(runner.get_snapshot())
    try:
        while True:
            data = await websocket.receive_json()
            # Handle incoming commands
            action = data.get("action")
            if action == "play":
                runner.play()
            elif action == "pause":
                runner.pause()
            elif action == "reset":
                runner.reset()
            elif action == "step":
                runner.step(dt_real_sec=0.5)
            elif action == "set_speed":
                runner.set_speed_multiplier(float(data.get("speed", 1.0)))
            elif action == "seek":
                runner.seek_fraction(float(data.get("fraction", 0.0)))
            elif action == "select_scenario":
                sc_id = data.get("scenario_id")
                if sc_id in ALL_SCENARIOS:
                    runner.load_scenario(sc_id)
            elif action == "tune":
                rec = data.get("receiver")
                st_id = data.get("station_id")
                obs = data.get("obs_deg")
                if rec == "nav1":
                    runner.avionics.tune_nav1(st_id, obs)
                elif rec == "nav2":
                    runner.avionics.tune_nav2(st_id, obs)
                elif rec == "dme1":
                    runner.avionics.tune_dme1(st_id)
                elif rec == "adf1":
                    runner.avionics.tune_adf1(st_id)

            snapshot = runner.get_snapshot()
            await manager.broadcast(snapshot)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# Mount UI build if it exists
UI_DIST = os.path.join(ROOT_DIR, "ui", "dist")
if os.path.exists(UI_DIST):
    app.mount("/", StaticFiles(directory=UI_DIST, html=True), name="ui")

