import logging.config
from contextlib import asynccontextmanager

from app.config.log_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.car_control.car_service import CarService
from app.services.connection_service import ConnectionService
from app.util.logger import Logger

description = """
`Picar-X Control App` is a project aimed at controlling the [Picar-X vehicle](https://docs.sunfounder.com/projects/picar-x/en/stable/) using WebSockets.

It integrates endpoints to manage the car's movement, calibration, and ultrasonic measurements. 🚀

It provides endpoints for:
- ultrasonic distance measurement
- WebSockets for controlling the car and calibration

This server runs in a separate process from the main server to ensure that control operations are never blocked.
"""

Logger.setup_from_env()

logger = Logger(name=__name__, app_name="px-control")

car_manager = CarService()
connection_manager = ConnectionService(notifier=car_manager, app_name="px-control")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.car_manager = car_manager
    app.state.connection_manager = connection_manager
    port = app.state.port if hasattr(app.state, "port") else 8001
    logger.info(f"Starting Car Control App on the port {port}")
    yield
    logger.info("Stopping application")


app = FastAPI(
    title="Picar X Racer Control App",
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


from app.api.control import car_manager_router, ultrasonic_router

app.include_router(car_manager_router)
app.include_router(ultrasonic_router)
