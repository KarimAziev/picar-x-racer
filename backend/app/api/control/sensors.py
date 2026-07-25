"""Diagnostics and bounded telemetry for localization sensors."""

import asyncio
from typing import Annotated

from app.api import robot_deps
from app.core.px_logger import Logger
from app.schemas.autonomy import LocalizationSensorStatus, OccupancyGrid
from app.services.autonomy import (
    LocalizationSensorService,
    SensorTelemetryStreamer,
    TopicBus,
    parse_telemetry_channels,
)
from app.services.autonomy.topics import LOCAL_MAP
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)
from starlette.websockets import WebSocketState


router = APIRouter()
_log = Logger(__name__)


@router.get(
    "/px/api/sensors/status",
    response_model=LocalizationSensorStatus,
    summary="Retrieve LiDAR, IMU, and encoder publisher diagnostics",
)
def get_localization_sensor_status(
    sensor_service: Annotated[
        LocalizationSensorService,
        Depends(robot_deps.get_localization_sensor_service),
    ],
) -> LocalizationSensorStatus:
    return sensor_service.status


@router.get(
    "/px/api/map/current",
    response_model=OccupancyGrid,
    summary="Retrieve the latest native local occupancy grid",
)
def get_current_local_map(
    topic_bus: Annotated[TopicBus, Depends(robot_deps.get_robot_topic_bus)],
) -> OccupancyGrid:
    current_map = topic_bus.latest(LOCAL_MAP)
    if current_map is None:
        raise HTTPException(status_code=404, detail="No local map has been published")
    return current_map


async def _wait_for_disconnect(websocket: WebSocket) -> None:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return


async def _close_telemetry_websocket(
    websocket: WebSocket, *, peer_disconnected: bool
) -> None:
    """Close a telemetry socket when the ASGI connection is still open.

    The receive and send tasks finish independently.  A browser disconnect can
    therefore race with this handler's cleanup, and Uvicorn rejects a second
    ``websocket.close`` ASGI message.  ``client_state`` covers the normal
    disconnect path; the RuntimeError guard handles the small remaining race
    between checking state and sending the close frame.
    """
    if peer_disconnected:
        return
    if (
        websocket.application_state != WebSocketState.CONNECTED
        or websocket.client_state != WebSocketState.CONNECTED
    ):
        return

    try:
        await websocket.close()
    except RuntimeError as error:
        if "Unexpected ASGI message 'websocket.close'" not in str(error):
            raise
        _log.debug("Telemetry websocket was already closed during cleanup")


@router.websocket("/px/ws/telemetry")
async def stream_localization_telemetry(
    websocket: WebSocket,
    topic_bus: Annotated[TopicBus, Depends(robot_deps.get_robot_topic_bus)],
    channels: Annotated[
        str,
        Query(
            description=(
                "Comma-separated lidar, imu, encoder, odometry, and safety channels"
            )
        ),
    ] = "lidar,imu,encoder,odometry,safety",
    rate_hz: Annotated[
        float,
        Query(ge=0.5, le=30, description="Maximum browser telemetry rate"),
    ] = 5.0,
) -> None:
    try:
        selected_channels = parse_telemetry_channels(channels)
    except ValueError as error:
        await websocket.close(code=1008, reason=str(error))
        return

    await websocket.accept()
    streamer = SensorTelemetryStreamer(
        topic_bus,
        channels=selected_channels,
        max_rate_hz=rate_hz,
    )
    send_task = asyncio.create_task(
        streamer.stream(websocket.send_json),
        name="sensor-telemetry-send",
    )
    disconnect_task = asyncio.create_task(
        _wait_for_disconnect(websocket),
        name="sensor-telemetry-disconnect",
    )
    peer_disconnected = False
    try:
        done, _ = await asyncio.wait(
            (send_task, disconnect_task),
            return_when=asyncio.FIRST_COMPLETED,
        )
        peer_disconnected = disconnect_task in done
        for task in done:
            task.result()
    except WebSocketDisconnect:
        peer_disconnected = True
        pass
    except asyncio.CancelledError:
        raise
    except Exception as error:
        _log.warning("Sensor telemetry connection ended: %s", error)
    finally:
        for task in (send_task, disconnect_task):
            if not task.done():
                task.cancel()
        await asyncio.gather(send_task, disconnect_task, return_exceptions=True)
        await _close_telemetry_websocket(
            websocket,
            peer_disconnected=peer_disconnected,
        )
