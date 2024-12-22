from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.paths import DEFAULT_USER_SETTINGS, PX_SETTINGS_FILE
from app.util.logger import Logger

description = """
`Picar-X Robot` is a project aimed at controlling the [Picar-X vehicle](https://docs.sunfounder.com/projects/picar-x/en/stable/) using WebSockets.

It integrates endpoints to manage the car's movement, calibration, and ultrasonic measurements. 🚀

It provides endpoints for:
- ultrasonic distance measurement
- WebSockets for controlling the car and calibration

This server runs in a separate process from the main server to ensure that control operations are never blocked.
"""

Logger.setup_from_env()

logger = Logger(name=__name__, app_name="px_robot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.api import robot_deps

    async_manager = robot_deps.get_async_task_manager()
    connection_manager = robot_deps.get_connection_manager()
    event_emitter = robot_deps.get_async_event_emitter()
    distance_service = robot_deps.get_distance_service(
        emitter=event_emitter, task_manager=async_manager
    )

    async def broadcast_distance(distance: float):
        await connection_manager.broadcast_json(
            {"type": "distance", "payload": distance}
        )

    distance_service.subscribe(broadcast_distance)
    settings = (
        load_json_file(PX_SETTINGS_FILE)
        if os.path.exists(PX_SETTINGS_FILE)
        else load_json_file(DEFAULT_USER_SETTINGS)
    )
    robot_settings = settings.get("robot", {})
    distance_interval = robot_settings.get("auto_measure_distance_delay_ms", 1000)
    distance_secs = distance_interval / 1000
    distance_service.interval = distance_secs
    auto_measure_distance_mode = robot_settings.get("auto_measure_distance_mode", False)
    if auto_measure_distance_mode:
        await distance_service.start_all()

    port = app.state.port if hasattr(app.state, "port") else 8001
    logger.info(f"Starting {app.title} app on the port {port}")
    yield
    await distance_service.cleanup()
    logger.info(f"Stopped {app.title}")


app = FastAPI(
    title="Picar-X Robot",
    version="0.0.1",
    description=description,
    lifespan=lifespan,
    contact={
        "name": "Karim Aziiev",
        "url": "http://github.com/KarimAziev/picar-x-racer",
        "email": "karim.aziiev@gmail.com",
    },
    license_info={
        "name": "GPL-3.0-or-later",
        "url": "https://www.gnu.org/licenses/gpl-3.0.en.html",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


import os

from app.api.control import car_manager_router, ultrasonic_router
from app.util.file_util import load_json_file

app.include_router(car_manager_router)
app.include_router(ultrasonic_router)
