from typing import TYPE_CHECKING

from app.api.deps import get_camera_manager, get_connection_manager, get_stream_manager
from app.config.video_enhancers import frame_enhancers
from app.schemas.stream import EnhancersResponse, StreamSettings
from app.util.logger import Logger
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from app.services.camera_service import CameraService
    from app.services.connection_service import ConnectionService
    from app.services.stream_service import StreamService

logger = Logger(__name__)


router = APIRouter()


@router.post(
    "/api/video-feed/settings",
    response_model=StreamSettings,
    summary="Update video feed settings with enhanced parameters for video streaming.",
)
async def update_video_feed_settings(
    request: Request,
    payload: StreamSettings,
    camera_manager: "CameraService" = Depends(get_camera_manager),
):
    """
    Update the video feed settings.

    Example Payload:
    --------------
    ```json
    {
        "format": ".jpg",
        "quality": 95,
        "enhance_mode": "simulate_predator_vision",
        "video_record": true,
        "render_fps": true
    }
    ```

    Args:
    --------------
    - `request` (Request): FastAPI request object used to access app state and app manager.
    - `payload` (StreamSettings): New video stream settings to apply.
    - `camera_manager` (CameraService): Camera management service for handling stream operations.

    Returns:
    --------------
    `StreamSettings`: The updated video stream settings.
    Additionally, broadcasts the updated settings to all connected clients.

    Raises:
    --------------
    None
    """
    logger.info("Video feed update payload %s", payload)
    connection_manager: "ConnectionService" = request.app.state.app_manager
    result: StreamSettings = await camera_manager.update_stream_settings(payload)
    await connection_manager.broadcast_json(
        {"type": "stream", "payload": result.model_dump()}
    )
    return result


@router.get(
    "/api/video-feed/settings",
    response_model=StreamSettings,
    summary="Retrieve the current video feed settings.",
    response_description="""
    Attributes:

    - format: The file format to save frames (e.g., '.jpg', '.png').
    - quality: Quality compression level for frames (0–100).
    - enhance_mode: Enhancer to apply to frames (e.g., 'simulate_predator_vision').
    - video_record: Whether the video stream should be recorded.
    - render_fps: Whether to render the video FPS.
    """,
)
def get_video_settings(
    camera_manager: "CameraService" = Depends(get_camera_manager),
):
    """
    Retrieve the current video feed settings.

    Args:
    --------------
    - `camera_manager` (CameraService): Camera management service for retrieving stream settings.

    Returns:
    --------------
    `StreamSettings`: Current video stream configuration data.
    """
    return camera_manager.stream_settings


@router.websocket(
    "/ws/video-stream",
)
async def ws(
    websocket: WebSocket,
    stream_service: "StreamService" = Depends(get_stream_manager),
    connection_manager: "ConnectionService" = Depends(get_connection_manager),
):
    """
    WebSocket endpoint for providing a video stream.

    Args:
    --------------
    - websocket (WebSocket): The WebSocket connection for streaming video.
    - stream_service (StreamService): The service responsible for handling video streams.

    Exceptions:
    --------------
    - `WebSocketDisconnect`: Handles the case where the WebSocket connection is closed.
    - `Exception`: Logs any other exceptions that occur during the video stream.
    """

    try:
        await websocket.accept()
        await stream_service.video_stream(websocket, connection_manager)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.log_exception("Error in video stream: ", e)


@router.get(
    "/api/video-feed/enhancers",
    response_model=EnhancersResponse,
    summary="Retrieve a list of available video frame enhancers.",
    response_description="""
    | Enhancer                            | Description                                                                       |
    | ----------------------------------- | --------------------------------------------------------------------------------- |
    | `simulate_robocop_vision`           | Video effect to simulate RoboCop vision.                                          |
    | `simulate_predator_vision`          | Thermal effect to simulate Predator vision.                                       |
    | `simulate_infrared_vision`          | Highlights warmer areas.                                                          |
    | `simulate_ultrasonic_vision`        | A monochromatic sonar effect.                                                     |
    | `preprocess_frame`                  | Enhances video quality.                                                           |
    | `preprocess_frame_clahe`            | Enhances contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization). |
    | `preprocess_frame_edge_enhancement` | Highlights object boundaries.                                                     |
    | `preprocess_frame_ycrcb`            | Transforms the image into the YCrCb color space.                                  |
    | `preprocess_frame_hsv_saturation`   | Increases saturation in the HSV color space.                                      |
    | `preprocess_frame_kmeans`           | Performs K-means clustering for image segmentation.                               |
    | `preprocess_frame_combined`         | Applies multiple preprocessing techniques.                                        |
    """,
)
def get_frame_enhancers():
    """
    Retrieve a list of available frame enhancers.

    Returns:
    --------------
    `EnhancersResponse`: A list of available frame enhancer names.
    """
    return {"enhancers": list(frame_enhancers.keys())}
