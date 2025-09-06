"""
Endpoints for handling video feed settings and WebSocket connections for streaming real-time video.
"""

from typing import TYPE_CHECKING, Annotated

from app.api import deps
from app.config.video_enhancers import frame_enhancers
from app.core.logger import Logger
from app.exceptions.camera import (
    CameraDeviceError,
    CameraNotFoundError,
    CameraShutdownInProgressError,
)
from app.schemas.stream import EnhancersResponse, StreamSettings
from app.services.connection_service import ConnectionService
from app.util.doc_util import build_response_description
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)

if TYPE_CHECKING:
    from app.services.camera.camera_service import CameraService
    from app.services.camera.stream_service import StreamService

_log = Logger(__name__)


router = APIRouter()


@router.post(
    "/video-feed/settings",
    response_model=StreamSettings,
    summary="Update video feed settings with enhanced parameters for video streaming.",
    response_description=(
        build_response_description(StreamSettings, "The updated video stream settings:")
    ),
)
async def update_video_feed_settings(
    request: Request,
    payload: StreamSettings,
    camera_manager: Annotated["CameraService", Depends(deps.get_camera_service)],
):
    """
    Update the video feed settings and broadcasts the updated settings to all
    connected clients.
    """
    _log.info("Video feed update payload %s", payload)

    connection_manager: "ConnectionService" = request.app.state.app_manager
    try:
        result: StreamSettings = await camera_manager.update_stream_settings(payload)
        await connection_manager.broadcast_json(
            {"type": "stream", "payload": result.model_dump()}
        )
        return result
    except (CameraDeviceError, CameraNotFoundError) as err:
        err_msg = str(err)
        _log.error(err_msg)
        await connection_manager.error(err_msg)
        raise HTTPException(status_code=400, detail=str(err))
    except CameraShutdownInProgressError as err:
        raise HTTPException(status_code=503, detail=str(err))
    except Exception as err:
        _log.error("Unexpected error while updating video feed settings", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update stream settings")


@router.get(
    "/video-feed/settings",
    response_model=StreamSettings,
    summary="Retrieve the current video feed settings.",
    response_description=(
        build_response_description(
            StreamSettings,
            "Current video stream configuration data with such attributes",
        )
    ),
)
def get_video_settings(
    camera_manager: Annotated["CameraService", Depends(deps.get_camera_service)],
):
    """
    Retrieve the current video feed settings.
    """
    return camera_manager.stream_settings


@router.websocket(
    "/ws/video-stream",
)
async def ws(
    websocket: WebSocket,
    stream_service: Annotated["StreamService", Depends(deps.get_stream_service)],
):
    """
    WebSocket endpoint for providing a video stream, including an embedded timestamp.

    Each frame is encoded as a byte array, prefixed by the frame's timestamp (as
    double-precision floating point format).
    """
    try:
        await websocket.accept()
        await stream_service.video_stream(websocket)
    except WebSocketDisconnect:
        pass
    except RuntimeError as e:
        _log.error("Runtime error in video stream: %s", e)
    except Exception:
        _log.error("Unexpected error in video stream: ", exc_info=True)


@router.get(
    "/video-feed/enhancers",
    response_model=EnhancersResponse,
    summary="Retrieve a list of available video effects.",
    response_description="A list of available video frame enhancers such as:"
    "\n"
    "- **robocop_vision**:                     Video effect to simulate RoboCop vision."
    "\n"
    "- **predator_vision**:                    Thermal effect to simulate Predator vision."
    "\n"
    "- **infrared_vision**:                    Highlights warmer areas."
    "\n"
    "- **ultrasonic_vision**:                  A monochromatic sonar effect."
    "\n"
    "- **brightness**:                         Increase brightness."
    "\n"
    "- **clahe**:                              Enhances contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)."
    "\n"
    "- **edge_enhancement**:                   Highlights object boundaries."
    "\n"
    "- **ycrcb**:                              Transforms the image into the YCrCb color space."
    "\n"
    "- **combined**:                           Applies multiple preprocessing techniques."
    "\n",
)
def get_frame_enhancers():
    """
    Retrieve a list of available frame enhancers.
    """
    return {"enhancers": list(frame_enhancers.keys())}
