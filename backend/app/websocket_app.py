import json
import logging.config

from app.config.log_config import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)


from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.car_controller import CarController
from app.schemas.distance import DistanceData
from app.util.logger import Logger

Logger.setup_from_env()

logger = Logger(name=__name__, app_name="px-control")

car_manager = CarController()
car_manager_router = APIRouter()

app = FastAPI(title="px-control")


@car_manager_router.get("/px/api/get-distance", response_model=DistanceData)
async def get_ultrasonic_distance():
    value: float = await car_manager.px.get_distance()
    return {"distance": value}


@car_manager_router.websocket("/px/ws")
async def websocket_endpoint(websocket: WebSocket):
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
