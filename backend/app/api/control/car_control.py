import json
from typing import TYPE_CHECKING

from app.util.logger import Logger
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = Logger(name=__name__, app_name="px-control")

car_manager_router = APIRouter()

if TYPE_CHECKING:
    from app.services.car_control.car_service import CarService
    from app.services.car_control.connection_service import ConnectionService


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
    connection_manager: "ConnectionService" = websocket.app.state.connection_manager
    await connection_manager.connect(websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            action: str = data.get("action")
            payload = data.get("payload")

            logger.info(f"Received data: {data}")

            if action:
                if websocket.application_state == "DISCONNECTED":
                    connection_manager.disconnect(websocket)
                else:
                    try:
                        await car_manager.process_action(action, payload, websocket)
                        await connection_manager.broadcast()
                    except RuntimeError as ex:
                        logger.error(
                            f"Failed to send error message due to RuntimeError: {ex}"
                        )
            else:
                logger.warning(f"Received invalid message: {data}")
    except WebSocketDisconnect:
        logger.info("WebSocket Disconnected")
        connection_manager.disconnect(websocket)
    except KeyboardInterrupt:
        logger.info("WebSocket interrupted")
        connection_manager.disconnect(websocket)
        await websocket.close()
