"""
The application provides robot-controlling functionality, including:

- WebSockets for controlling and calibration of the robot
- ultrasonic distance measurement
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.control import api_router, tags_metadata
from app.config.config import settings as app_settings
from app.core.logger import Logger

Logger.setup_from_env()


logger = Logger(name=__name__, app_name="px_robot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os

    from app.api import robot_deps
    from app.util.file_util import load_json_file

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
        load_json_file(app_settings.PX_SETTINGS_FILE)
        if os.path.exists(app_settings.PX_SETTINGS_FILE)
        else load_json_file(app_settings.DEFAULT_USER_SETTINGS)
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
    title="Robot Control Application",
    version="0.0.1",
    summary="API for the robot's hardware interactions.",
    description=__doc__ or "",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    contact={
        "name": "Karim Aziiev",
        "email": "karim.aziiev@gmail.com",
    },
    license_info={
        "name": "GNU General Public License v3.0 or later",
        "identifier": "GPL-3.0-or-later",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
