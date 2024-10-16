import json
from typing import TYPE_CHECKING

from app.util.logger import Logger
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = Logger(name=__name__, app_name="px-control")

car_manager_router = APIRouter()

if TYPE_CHECKING:
    from app.services.car_control.car_service import CarService


@car_manager_router.websocket("/px/ws")
async def websocket_endpoint(
    websocket: WebSocket,
):
    """
    WebSocket endpoint for controlling the Picar-X vehicle.

    Args:
        websocket (WebSocket): The WebSocket connection for sending and receiving control commands.

    Raises:
        Exception: If there is an error processing the incoming message.
        WebSocketDisconnect: If the WebSocket connection is disconnected.
        KeyboardInterrupt: If the WebSocket connection is interrupted.
    """
    car_manager: "CarService" = websocket.app.state.car_manager
    await websocket.accept()
    await car_manager.handle_notify_client(websocket)
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
