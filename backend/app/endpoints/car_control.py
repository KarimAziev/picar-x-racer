import json
from typing import TYPE_CHECKING

from app.deps import get_car_manager
from app.util.logger import Logger
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from app.controllers.car_controller import CarController


router = APIRouter()
logger = Logger(__name__)


@router.websocket("/ws/car-control")
async def websocket_endpoint(
    websocket: WebSocket, car_manager: "CarController" = Depends(get_car_manager)
):
    await websocket.accept()

    try:
        async for raw_data in websocket.iter_text():
            try:
                data = json.loads(raw_data)
                action = data.get("action")
                payload = data.get("payload")
                logger.info(f"data {data}")
                if action:
                    await car_manager.process_action(action, payload, websocket)
                else:
                    logger.info(f"received invalid message {data}")
            except WebSocketDisconnect:
                logger.info("WebSocket Disconnected")
                break
            except Exception as e:
                logger.error(f"Car controller error occurred: {e}")
    except WebSocketDisconnect:
        logger.info("WebSocket Disconnected")
