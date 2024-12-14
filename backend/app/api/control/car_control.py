import asyncio
import json
from typing import TYPE_CHECKING

from app.util.logger import Logger
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = Logger(name=__name__, app_name="px-control")

car_manager_router = APIRouter()

if TYPE_CHECKING:
    from app.services.car_control.car_service import CarService
    from app.services.connection_service import ConnectionService


@car_manager_router.websocket("/px/ws")
async def websocket_endpoint(
    websocket: WebSocket,
):
    """
    WebSocket endpoint for controlling the Picar-X vehicle.

    Args:
        websocket (WebSocket): The WebSocket connection for sending and receiving control commands.

    Raises:
        Exception: If there is an error while processing the incoming message.
        WebSocketDisconnect: If the WebSocket connection disconnects.
        KeyboardInterrupt: If the WebSocket connection is interrupted.
    """
    car_manager: "CarService" = websocket.app.state.car_manager
    connection_manager: "ConnectionService" = websocket.app.state.connection_manager
    battery_manager = websocket.app.state.battery_manager

    try:
        await connection_manager.connect(websocket)
        await car_manager.broadcast()

        while websocket.application_state == WebSocketState.CONNECTED:
            # Set up asynchronous "race" between receiving a message or a timeout for idle actions
            raw_data_task = asyncio.create_task(websocket.receive_text())
            timeout_task = asyncio.create_task(
                asyncio.sleep(1)
            )  # 1-second delay for timeout

            done, pending = await asyncio.wait(
                {raw_data_task, timeout_task}, return_when=asyncio.FIRST_COMPLETED
            )

            # Determine the winner
            if raw_data_task in done:  # A message was received
                # Cancel the timeout task since it's no longer needed
                timeout_task.cancel()

                # Get the received WebSocket message and process it
                raw_data = await raw_data_task
                data = json.loads(raw_data)
                action: str = data.get("action")
                payload = data.get("payload")
                logger.debug("%s", data)

                await car_manager.process_action(action, payload, websocket)

            elif timeout_task in done:  # Timeout occurred, perform idle actions
                # Cancel the raw data task since we will handle the timeout
                raw_data_task.cancel()

                # Perform idle task (e.g., measuring voltage and sending via WebSocket)
                voltage_data = await measure_voltage(battery_manager)
                await websocket.send_text(json.dumps(voltage_data))

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
