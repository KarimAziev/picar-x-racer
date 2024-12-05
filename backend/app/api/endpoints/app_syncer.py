import asyncio
import json
from typing import TYPE_CHECKING

from app.api.deps import get_camera_manager, get_detection_manager, get_music_manager
from app.util.logger import Logger
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

if TYPE_CHECKING:
    from app.services.camera_service import CameraService
    from app.services.connection_service import ConnectionService
    from app.services.detection_service import DetectionService
    from app.services.music_service import MusicService


logger = Logger(__name__)


router = APIRouter()


@router.websocket("/ws/sync")
async def app_synchronizer(
    websocket: WebSocket,
    detection_service: "DetectionService" = Depends(get_detection_manager),
    camera_service: "CameraService" = Depends(get_camera_manager),
    music_service: "MusicService" = Depends(get_music_manager),
):
    connection_manager: "ConnectionService" = websocket.app.state.app_manager

    try:
        await connection_manager.connect(websocket)
        await music_service.broadcast_state()
        data = {
            "camera": camera_service.camera_settings.model_dump(),
            "stream": camera_service.stream_settings.model_dump(),
            "detection": detection_service.detection_settings.model_dump(),
            "active_connections": len(connection_manager.active_connections),
        }
        for key, value in data.items():
            await connection_manager.broadcast_json({"type": key, "payload": value})

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
        logger.info("Synchronization WebSocket Disconnected")
        connection_manager.remove(websocket)
    except asyncio.CancelledError:
        logger.info("Gracefully shutting down Synchronization WebSocket connection")
        await connection_manager.disconnect(websocket)
    except KeyboardInterrupt:
        logger.info("Synchronization WebSocket interrupted")
        await connection_manager.disconnect(websocket)
    finally:
        connection_manager.remove(websocket)
        await connection_manager.broadcast_json(
            {
                "type": "active_connections",
                "payload": len(connection_manager.active_connections),
            }
        )
