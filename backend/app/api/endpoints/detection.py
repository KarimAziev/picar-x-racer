import asyncio
from typing import TYPE_CHECKING

from app.api.deps import get_detection_manager
from app.config.yolo_common_models import get_available_models
from app.schemas.detection import DetectionSettings
from app.util.logger import Logger
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.detection_service import DetectionService

logger = Logger(__name__)


detection_router = APIRouter()


@detection_router.post("/api/detection-settings", response_model=DetectionSettings)
async def update_detection_settings(
    request: Request,
    payload: DetectionSettings,
    detection_service: "DetectionService" = Depends(get_detection_manager),
):
    connection_manager: "ConnectionService" = request.app.state.app_manager
    result = await detection_service.update_detection_settings(payload)
    logger.info(f"result={result}")
    await connection_manager.broadcast_json(
        {"type": "detection", "payload": result.model_dump()}
    )

    return result


@detection_router.get("/api/detection-settings", response_model=DetectionSettings)
def get_detection_settings(
    detection_service: "DetectionService" = Depends(get_detection_manager),
):
    return detection_service.detection_settings


@detection_router.websocket("/ws/object-detection")
async def object_detection(
    websocket: WebSocket,
    detection_service: "DetectionService" = Depends(get_detection_manager),
):
    connection_manager: "ConnectionService" = websocket.app.state.detection_notifier
    try:
        await connection_manager.connect(websocket)
        while websocket.application_state == WebSocketState.CONNECTED:
            if detection_service.stop_event.is_set():
                await connection_manager.disconnect(websocket)
                break
            await asyncio.to_thread(detection_service.get_detection)
            if detection_service.stop_event.is_set():
                await connection_manager.disconnect(websocket)
                break
            await connection_manager.broadcast_json(detection_service.current_state)

    except WebSocketDisconnect:
        logger.info("Detection WebSocket Disconnected")
    except asyncio.CancelledError:
        logger.info("Gracefully shutting down Detection WebSocket connection")
        await connection_manager.disconnect(websocket)
    except KeyboardInterrupt:
        logger.info("Detection WebSocket interrupted")
        await connection_manager.disconnect(websocket)
    finally:
        connection_manager.remove(websocket)


@detection_router.get("/api/detection-models")
def get_detectors():
    """
    Retrieve a list of available object detectors.
    """
    return get_available_models()
