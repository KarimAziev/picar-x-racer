import asyncio
from typing import TYPE_CHECKING, List

from app.api import deps
from app.exceptions.detection import DetectionModelLoadError, DetectionProcessError
from app.schemas.detection import DetectionSettings, FileNode
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
    from app.services.file_service import FileService

logger = Logger(__name__)


router = APIRouter()


@router.post(
    "/detection/settings",
    response_model=DetectionSettings,
    summary="Update Detection Settings",
    response_description="Returns the updated detection settings:"
    "\n"
    "- **model**: The name of the object detection model to be used."
    "\n"
    "- **confidence**: The confidence threshold for detections."
    "\n"
    "- **active**: Flag indicating whether the detection is currently active."
    "\n"
    "- **img_size**: The image size for the detection process."
    "\n"
    "- **labels**: A list of labels to filter for specific object detections, if desired."
    "\n"
    "- **overlay_draw_threshold**: The maximum allowable time difference (in seconds) "
    "between the frame timestamp and the detection timestamp for overlay drawing to occur.",
    responses={
        400: {
            "description": "Bad Request - Errors like model loading or detection issues.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Model's file /home/pi/picar-x-racer/data/yolov3n.pt is not found"
                    }
                }
            },
        }
    },
)
async def update_detection_settings(
    request: Request,
    payload: DetectionSettings,
    detection_service: "DetectionService" = Depends(deps.get_detection_manager),
):
    """
    Endpoint to update object detection settings.

    Updates detection settings, notifies all connected clients via WebSocket and
    returns the updated settings.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    logger.info("Detection update payload %s", payload)
    try:
        await connection_manager.broadcast_json(
            {"type": "detection-loading", "payload": True}
        )
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
        raise HTTPException(status_code=400, detail=str(e))
    except DetectionProcessError as e:
        detection_service.detection_settings.active = False
        await connection_manager.broadcast_json(
            {
                "type": "detection",
                "payload": detection_service.detection_settings.model_dump(),
            }
        )
        raise HTTPException(status_code=400, detail=f"Detection error {e}")
    finally:
        await connection_manager.broadcast_json(
            {"type": "detection-loading", "payload": False}
        )


@router.get(
    "/detection/settings",
    response_model=DetectionSettings,
    summary="Retrieve object detection settings",
    response_description="The current configuration of the object detection system: "
    "\n"
    "- **model**: The name of the object detection model to be used."
    "\n"
    "- **confidence**: The confidence threshold for detections."
    "\n"
    "- **active**: Flag indicating whether the detection is currently active."
    "\n"
    "- **img_size**: The image size for the detection process."
    "\n"
    "- **labels**: A list of labels to filter for specific object detections, if desired."
    "\n"
    "- **overlay_draw_threshold**: The maximum allowable time difference (in seconds) "
    "between the frame timestamp and the detection timestamp for overlay drawing to occur.",
)
def get_detection_settings(
    detection_service: "DetectionService" = Depends(deps.get_detection_manager),
):
    """
    Endpoint to retrieve the current detection configuration.

    Returns the current configuration of the object detection system.
    """
    return detection_service.detection_settings


@router.websocket("/ws/object-detection")
async def object_detection(
    websocket: WebSocket,
    detection_service: "DetectionService" = Depends(deps.get_detection_manager),
    detection_notifier: "ConnectionService" = Depends(deps.get_detection_notifier),
):
    """
    WebSocket endpoint for real-time object detection updates.

    Behavior:
    - Establishes a WebSocket connection for continuous object detection updates.
    - Gracefully handles connection interruptions or shutdowns.
    """
    try:
        await detection_notifier.connect(websocket)
        while websocket.application_state == WebSocketState.CONNECTED:
            if detection_service.stop_event.is_set():
                await detection_notifier.disconnect(websocket)
                break
            await asyncio.to_thread(detection_service.get_detection)
            if detection_service.stop_event.is_set():
                await detection_notifier.disconnect(websocket)
                break
            await detection_notifier.broadcast_json(detection_service.current_state)

    except WebSocketDisconnect:
        logger.info("Detection WebSocket Disconnected")
    except asyncio.CancelledError:
        logger.info("Gracefully shutting down Detection WebSocket connection")
        await detection_notifier.disconnect(websocket)
    except KeyboardInterrupt:
        logger.info("Detection WebSocket interrupted")
        await detection_notifier.disconnect(websocket)
    finally:
        detection_notifier.remove(websocket)


@router.get(
    "/detection/models",
    summary="Retrieve Available Detection Models",
    response_description="Returns a hierarchical tree structure representing the available object detection models, "
    "organized as a series of nodes. Each node in the tree can represent one of the following:"
    "\n"
    "- **Folder**: A container for sub-nodes (children) that includes other folders or files. "
    "Only those directories are included that have at least one valid model file at any depth."
    "\n"
    "- **File**: A specific file representing a concrete object detection model present on the filesystem."
    "\n"
    "- **Loadable model**: A virtual node that represents a detection model, which may not physically exist on the "
    "filesystem but is loadable (e.g., pre-trained models such as `yolov8n.pt`).",
    response_model=List[FileNode],
)
def get_detectors(file_manager: "FileService" = Depends(deps.get_file_manager)):
    """
    Retrieve a recursive tree structure representing the organized set of
    detection models and their associated metadata.
    """
    return file_manager.get_available_models()
