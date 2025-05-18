"""
The application provides robot-controlling functionality, including:

- WebSockets for controlling and calibration of the robot
- Ultrasonic distance measurement
- Battery monitoring

"""

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Optional, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.control import api_router, tags_metadata
from app.core.px_logger import Logger

if TYPE_CHECKING:
    from app.managers.file_management.json_data_manager import JsonDataManager
    from app.services.connection_service import ConnectionService
    from app.services.control.car_service import CarService
    from app.services.sensors.battery_service import BatteryService
    from app.services.sensors.distance_service import DistanceService
    from app.services.sensors.led_service import LEDService
    from app.services.sensors.speed_estimator import SpeedEstimator

Logger.setup_from_env()


logger = Logger(name=__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection_service: Optional["ConnectionService"] = None
    battery_service: Optional["BatteryService"] = None
    robot_service: Optional["CarService"] = None
    distance_service: Optional["DistanceService"] = None
    settings_service: Optional["JsonDataManager"] = None
    led_service: Optional["LEDService"] = None
    speed_estimator: Optional["SpeedEstimator"] = None

    try:

        from app.api import robot_deps
        from app.util.solve_lifespan import solve_lifespan

        lifespan_deps = solve_lifespan(robot_deps.get_lifespan_dependencies)
        async with lifespan_deps(app) as deps:
            connection_service = deps.get("connection_service")
            battery_service = deps.get("battery_service")
            robot_service = deps.get("robot_service")
            settings_service = deps.get("settings_service")
            distance_service = deps.get("distance_service")
            led_service = deps.get("led_service")
            speed_estimator = deps.get("speed_estimator")

        async def broadcast_distance(distance: float):
            rel_speed = (
                cast(int, robot_service.current_state["speed"]) if robot_service else 0
            )
            speed = (
                speed_estimator.process_distance(
                    distance,
                    distance_service.interval,
                    relative_speed=rel_speed,
                )
                if speed_estimator
                else None
            )
            await connection_service.broadcast_json(
                {"type": "distance", "payload": {"distance": distance, "speed": speed}}
            )

        battery_service.setup_connection_manager()
        distance_service.subscribe(broadcast_distance)

        settings = settings_service.load_data()
        robot_settings = settings.get("robot", {})

        distance_interval = robot_settings.get("auto_measure_distance_delay_ms", 1000)
        distance_secs = distance_interval / 1000

        distance_service.interval = distance_secs

        auto_measure_distance_mode = robot_settings.get(
            "auto_measure_distance_mode", False
        )

        if auto_measure_distance_mode:
            await distance_service.start_all()

        port = app.state.port if hasattr(app.state, "port") else 8001
        logger.info(f"Starting {app.title} app on the port {port}")

        yield
    except asyncio.CancelledError:
        logger.warning(
            "Lifespan was cancelled mid-shutdown (first-level). Proceeding to final cleanup."
        )

    if battery_service:
        try:
            await battery_service.cleanup_connection_manager()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up battery_service.")
            raise

    if robot_service:
        try:
            await robot_service.cleanup()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up robot_service.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup robot service: %s", e)

    if distance_service:
        try:
            await distance_service.cleanup()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up distance service.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup distance service: %s", e)

    if led_service:
        try:
            await led_service.cleanup()
        except asyncio.CancelledError:
            logger.warning("Cancelled while cleaning up LED service.")
            raise
        except Exception as e:
            logger.error("Failed to cleanup LED service: %s", e)

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
