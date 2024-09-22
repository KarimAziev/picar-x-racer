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
async def ws(
    websocket: WebSocket, car_manager: "CarController" = Depends(get_car_manager)
):
    await websocket.accept()

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                logger.info(f"data {data}")
                action = data.get("action")
                payload = data.get("payload")
                if action:
                    await car_manager.process_action(action, payload, websocket)
                else:
                    logger.info(f"received invalid message {data}")
            except Exception as e:
                logger.error(f"Car controller error occurred: {e}")
    except WebSocketDisconnect:
        logger.info("WebSocket Disconnected")
