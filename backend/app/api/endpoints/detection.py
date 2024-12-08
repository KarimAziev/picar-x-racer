import asyncio
from typing import TYPE_CHECKING, List

from app.api.deps import get_detection_manager, get_file_manager
from app.exceptions.detection import DetectionModelLoadError, DetectionProcessError
from app.schemas.detection import DetectionSettings, ModelResponse
from app.util.logger import Logger
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from starlette.websockets import WebSocketState

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.detection_service import DetectionService
    from app.services.files_service import FilesService

logger = Logger(__name__)


router = APIRouter()


@router.post(
    "/api/detection/settings",
    response_model=DetectionSettings,
    summary="Update Detection Settings",
    response_description="Returns the updated detection settings.",
)
async def update_detection_settings(
    request: Request,
    payload: DetectionSettings,
    detection_service: "DetectionService" = Depends(get_detection_manager),
):
    """
    Endpoint to update object detection settings.

    Args:
    -------------
    - payload (DetectionSettings): The new configuration for the object detection system.
    - detection_service (DetectionService): The service managing the object detection process.

    Returns:
    -------------
    DetectionSettings: The updated settings after applying configurations.

    Behavior:
    -------------
    - Updates detection settings and notifies connected clients via WebSocket.
    - Handles errors related to model loading or detection issues.

    Raises:
    -------------
    - HTTPException (400): If there is an error during model loading or detection.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    logger.info("Detection update payload %s", payload)
    try:
        result = await detection_service.update_detection_settings(payload)
        await connection_manager.broadcast_json(
            {"type": "detection", "payload": result.model_dump()}
        )
        return result
    except DetectionModelLoadError as e:
        detection_service.detection_settings.active = False
        await connection_manager.broadcast_json(
            {
                "type": "detection",
                "payload": detection_service.detection_settings.model_dump(),
            }
        )
        raise HTTPException(status_code=400, detail=f"Model loading error {e}")
    except DetectionProcessError as e:
        detection_service.detection_settings.active = False
        await connection_manager.broadcast_json(
            {
                "type": "detection",
                "payload": detection_service.detection_settings.model_dump(),
            }
        )
        raise HTTPException(status_code=400, detail=f"Detection error {e}")


@router.get(
    "/api/detection/settings",
    response_model=DetectionSettings,
    summary="Retrieve Detection Settings",
    response_description="Returns the current detection configuration.",
)
def get_detection_settings(
    detection_service: "DetectionService" = Depends(get_detection_manager),
):
    """
    Endpoint to retrieve the current detection configuration.

    Args:
    -------------
    - detection_service (DetectionService): The service managing the object detection process.

    Returns:
    -------------
    DetectionSettings: The current configuration of the object detection system.
    """
    return detection_service.detection_settings


@router.websocket("/ws/object-detection")
async def object_detection(
    websocket: WebSocket,
    detection_service: "DetectionService" = Depends(get_detection_manager),
):
    """
    WebSocket endpoint for real-time object detection updates.

    Args:
    -------------
    - websocket (WebSocket): The WebSocket connection for real-time communication.
    - detection_service (DetectionService): The detection service broadcasting updates.

    Behavior:
    -------------
    - Establishes a WebSocket connection for continuous object detection updates.
    - Gracefully handles connection interruptions or shutdowns.
    """
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


@router.get(
    "/api/detection/models",
    summary="Retrieve Available Detection Models",
    response_description="Returns a structed list of available object detection models.",
    response_model=List[ModelResponse],
)
def get_detectors(file_manager: "FilesService" = Depends(get_file_manager)):
    """
    Endpoint to retrieve a list of available object detection models.

    Returns:
    -------------
    List[Dict[str, Any]]: A list of available detection models that can be used for object detection.
    """
    return file_manager.get_available_models()
