import json
import logging.config

from app.config.log_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)


from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.schemas.distance import DistanceData
from app.services.car_control.car_service import CarService
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
car_manager_router = APIRouter()


app = FastAPI(
    title="Picar X Racer Control App",
    version="0.0.1",
    description=description,
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


@car_manager_router.get("/px/api/get-distance", response_model=DistanceData)
async def get_ultrasonic_distance():
    """
    Retrieve the current ultrasonic distance measurement from the Picar-X vehicle.

    Returns:
        DistanceData: The current distance measurement.
    """
    value: float = await car_manager.px.get_distance()
    return {"distance": value}


@car_manager_router.websocket("/px/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for controlling the Picar-X vehicle.

    Args:
        websocket (WebSocket): The WebSocket connection for sending and receiving control commands.

    Raises:
        Exception: If there is an error processing the incoming message.
        WebSocketDisconnect: If the WebSocket connection is disconnected.
        KeyboardInterrupt: If the WebSocket connection is interrupted.
    """
    await websocket.accept()
    try:
        async for raw_data in websocket.iter_text():
            try:
                data = json.loads(raw_data)
                action: str = data.get("action")
                payload = data.get("payload")

                logger.info(f"Received data: {data}")

                if action:
                    await car_manager.process_action(action, payload, websocket)
                else:
                    logger.warning(f"Received invalid message: {data}")

            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_text(f"Error: {str(e)}")

    except WebSocketDisconnect:
        logger.info("WebSocket Disconnected")
    except KeyboardInterrupt:
        logger.info("WebSocket interrupted")
        await websocket.close()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(car_manager_router)
