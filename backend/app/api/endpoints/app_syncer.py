"""
Websocket endpoint for synchronizing app state between several clients.
"""

import asyncio
import json
from typing import TYPE_CHECKING, Annotated

from app.api import deps
from app.core.logger import Logger
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

if TYPE_CHECKING:
    from app.services.camera.camera_service import CameraService
    from app.services.connection_service import ConnectionService
    from app.services.detection.detection_service import DetectionService
    from app.services.media.music_service import MusicService


_log = Logger(__name__)


router = APIRouter()


@router.websocket("/ws/sync")
async def app_synchronizer(
    websocket: WebSocket,
    detection_service: Annotated[
        "DetectionService", Depends(deps.get_detection_service)
    ],
    camera_service: Annotated["CameraService", Depends(deps.get_camera_service)],
    music_service: Annotated["MusicService", Depends(deps.get_music_service)],
):
    """
    Websocket endpoint for synchronizing app state between several clients.
    """
    connection_manager: "ConnectionService" = websocket.app.state.app_manager

    try:
        await connection_manager.connect(websocket)
        await music_service.broadcast_state()
        data = {
            "active_connections": len(connection_manager.active_connections),
            "camera": camera_service.camera_settings.model_dump(),
            "stream": camera_service.stream_settings.model_dump(),
            "camera_error": camera_service.camera_device_error,
        }
        for key, value in data.items():
            await connection_manager.broadcast_json({"type": key, "payload": value})

        if detection_service.loading:
            await connection_manager.broadcast_json(
                {"type": "detection-loading", "payload": True}
            )

        if (
            detection_service.detection_settings.active
            and not detection_service.loading
            and not detection_service.shutting_down
            and detection_service.detection_process is None
        ):
            if detection_service.detection_settings.model is None:
                detection_service.detection_settings.active = False
            else:
                await detection_service.start_detection_process()
                detection_service.detection_process_task = asyncio.create_task(
                    detection_service.detection_watcher()
                )

        await connection_manager.broadcast_json(
            {
                "type": "detection",
                "payload": detection_service.detection_settings.model_dump(),
            }
        )

        while websocket.application_state == WebSocketState.CONNECTED:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            action: str = data.get("action")
            payload = data.get("payload")
            action_handlers = {
                "update_detection": detection_service.update_detection_settings,
                "update_camera": camera_service.update_camera_settings,
                "update_stream": camera_service.update_stream_settings,
            }

            handler = action_handlers.get(action)
            if handler is not None:
                if asyncio.iscoroutinefunction(handler):
                    await handler(payload)
                else:
                    await asyncio.to_thread(handler, payload)

    except WebSocketDisconnect:
        _log.info("App Synchronizer: Synchronization WebSocket Disconnected")
        await connection_manager.disconnect(websocket, should_close=False)
    except asyncio.CancelledError:
        _log.info(
            "App Synchronizer: Gracefully shutting down Synchronization WebSocket connection"
        )
        await connection_manager.disconnect(websocket)
    except KeyboardInterrupt:
        _log.info("App Synchronizer: Synchronization WebSocket interrupted")
        await connection_manager.disconnect(websocket)
    finally:
        await connection_manager.broadcast_json(
            {
                "type": "active_connections",
                "payload": len(connection_manager.active_connections),
            }
        )
