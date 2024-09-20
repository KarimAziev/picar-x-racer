import json
from typing import TYPE_CHECKING

from app.util.logger import Logger
from quart import Blueprint, current_app, websocket

if TYPE_CHECKING:
    from app.controllers.car_controller import CarController


car_controller_bp = Blueprint("car_control", __name__)
logger = Logger(__name__)


@car_controller_bp.websocket("/ws/car-control")
async def ws():
    car_controller: "CarController" = current_app.config["car_manager"]
    while True:
        raw_data = await websocket.receive()
        try:
            data = json.loads(raw_data)
            logger.info(f"data {data}")
            action = data.get("action")
            payload = data.get("payload")
            if action:
                await car_controller.process_action(action, payload, websocket)
            else:
                logger.info(f"received invalid message {data}")
        except Exception as e:
            car_controller.logger.error(f"Car controller error occurred: {e}")
