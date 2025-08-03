"""
WebSocket endpoint for controlling and interacting with the robot.
"""

import asyncio
import json
from typing import TYPE_CHECKING, Annotated

from app.api import robot_deps
from app.core.px_logger import Logger
from app.exceptions.robot import RobotI2CBusError, RobotI2CTimeout
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = Logger(name=__name__)

router = APIRouter()

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.control.car_service import CarService
    from app.services.sensors.battery_service import BatteryService


@router.websocket("/px/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    car_manager: Annotated["CarService", Depends(robot_deps.get_robot_service)],
    connection_manager: Annotated[
        "ConnectionService", Depends(robot_deps.get_connection_manager)
    ],
    battery_manager: Annotated[
        "BatteryService", Depends(robot_deps.get_battery_service)
    ],
):
    """
    WebSocket endpoint for controlling the robot.
    """
    try:
        await connection_manager.connect(websocket)
        if len(connection_manager.active_connections) > 1:
            await battery_manager.broadcast_state()

        await car_manager.broadcast()

        while websocket.application_state == WebSocketState.CONNECTED:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            action: str = data.get("action")
            payload = data.get("payload")

            logger.debug("%s", data)
            try:
                await car_manager.process_action(action, payload, websocket)
            except (RobotI2CTimeout, RobotI2CBusError) as e:
                logger.error(str(e))
                await connection_manager.error(str(e))
            except Exception as e:
                logger.error(
                    "Unexpected error during action '%s' processing",
                    action,
                    exc_info=True,
                )
                await connection_manager.error("Unexpected robot error occurred")

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected gracefully.")
    except asyncio.CancelledError:
        logger.warning("WebSocket cancelled by application.")
        await connection_manager.disconnect(websocket)
    except KeyboardInterrupt:
        logger.warning("WebSocket connection interrupted.")
        await connection_manager.disconnect(websocket)
    finally:
        logger.info("Cleaning up WebSocket connection.")
        connection_manager.remove(websocket)
