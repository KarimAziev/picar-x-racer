"""
Endpoints for handling video feed settings and WebSocket connections for streaming real-time video.
"""

from typing import TYPE_CHECKING

from app.api import deps
from app.config.video_enhancers import frame_enhancers
from app.core.logger import Logger
from app.schemas.stream import EnhancersResponse, StreamSettings
from app.services.connection_service import ConnectionService
from app.util.doc_util import build_response_description
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from app.services.camera_service import CameraService
    from app.services.stream_service import StreamService

logger = Logger(__name__)


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
    camera_manager: "CameraService" = Depends(deps.get_camera_manager),
):
    """
    Update the video feed settings and broadcasts the updated settings to all
    connected clients.
    """
    logger.info("Video feed update payload %s", payload)
    connection_manager: "ConnectionService" = request.app.state.app_manager
    result: StreamSettings = await camera_manager.update_stream_settings(payload)
    await connection_manager.broadcast_json(
        {"type": "stream", "payload": result.model_dump()}
    )
    return result


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
    camera_manager: "CameraService" = Depends(deps.get_camera_manager),
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
    stream_service: "StreamService" = Depends(deps.get_stream_manager),
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
    except Exception:
        logger.error("Unexpected error in video stream: ", exc_info=True)


@router.get(
    "/video-feed/enhancers",
    response_model=EnhancersResponse,
    summary="Retrieve a list of available video effects.",
    response_description="A list of available video frame enhancers such as:"
    "\n"
    "- **simulate_robocop_vision**:            Video effect to simulate RoboCop vision."
    "\n"
    "- **simulate_predator_vision**:           Thermal effect to simulate Predator vision."
    "\n"
    "- **simulate_infrared_vision**:           Highlights warmer areas."
    "\n"
    "- **simulate_ultrasonic_vision**:         A monochromatic sonar effect."
    "\n"
    "- **preprocess_frame**:                   Enhances video quality."
    "\n"
    "- **preprocess_frame_clahe**:             Enhances contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)."
    "\n"
    "- **preprocess_frame_edge_enhancement**:  Highlights object boundaries."
    "\n"
    "- **preprocess_frame_ycrcb**:             Transforms the image into the YCrCb color space."
    "\n"
    "- **preprocess_frame_hsv_saturation**:    Increases saturation in the HSV color space."
    "\n"
    "- **preprocess_frame_kmeans**:            Performs K-means clustering for image segmentation."
    "\n"
    "- **preprocess_frame_combined**:          Applies multiple preprocessing techniques."
    "\n",
)
def get_frame_enhancers():
    """
    Retrieve a list of available frame enhancers.
    """
    return {"enhancers": list(frame_enhancers.keys())}
