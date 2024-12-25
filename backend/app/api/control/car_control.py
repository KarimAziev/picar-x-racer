import asyncio
import json
from typing import TYPE_CHECKING

from app.api import robot_deps
from app.util.logger import Logger
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = Logger(name=__name__, app_name="px_robot")

car_manager_router = APIRouter()

if TYPE_CHECKING:
    from app.services.car_control.calibration_service import CalibrationService
    from app.services.car_control.car_service import CarService
    from app.services.connection_service import ConnectionService


@car_manager_router.websocket("/px/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    car_manager: "CarService" = Depends(robot_deps.get_robot_manager),
    calibration_service: "CalibrationService" = Depends(
        robot_deps.get_calibration_service
    ),
    connection_manager: "ConnectionService" = Depends(
        robot_deps.get_connection_manager
    ),
):
    """
    WebSocket endpoint for controlling the Picar-X vehicle.

    Raises:
        Exception: If there is an error processing the incoming message.
        WebSocketDisconnect: If the WebSocket connection is disconnected.
        KeyboardInterrupt: If the WebSocket connection is interrupted.
    """
    try:
        await connection_manager.connect(websocket)
        await connection_manager.broadcast_json(
            {
                "type": "updateCalibration",
                "payload": calibration_service.get_calibration_data(),
            }
        )
        await car_manager.broadcast()

        while websocket.application_state == WebSocketState.CONNECTED:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            action: str = data.get("action")
            payload = data.get("payload")

            logger.debug("%s", data)
            await car_manager.process_action(action, payload, websocket)

    except WebSocketDisconnect:
        logger.info("WebSocket Disconnected")
    except asyncio.CancelledError:
        logger.info("Gracefully shutting down Detection WebSocket connection")
        await connection_manager.disconnect(websocket)
    except KeyboardInterrupt:
        logger.info("WebSocket interrupted")
        await connection_manager.disconnect(websocket)
    finally:
        connection_manager.remove(websocket)
