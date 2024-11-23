import asyncio
from typing import TYPE_CHECKING

from app.api.deps import get_camera_manager, get_stream_manager
from app.config.video_enhancers import frame_enhancers
from app.schemas.stream import EnhancersResponse, StreamSettings
from app.services.connection_service import ConnectionService
from app.util.logger import Logger
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from app.services.camera_service import CameraService
    from app.services.stream_service import StreamService

logger = Logger(__name__)


video_feed_router = APIRouter()


@video_feed_router.post("/api/video-feed-settings", response_model=StreamSettings)
async def update_video_feed_settings(
    request: Request,
    payload: StreamSettings,
    camera_manager: "CameraService" = Depends(get_camera_manager),
):
    connection_manager: "ConnectionService" = request.app.state.app_manager
    result: StreamSettings = await asyncio.to_thread(
        camera_manager.update_stream_settings, payload
    )
    await connection_manager.broadcast_json(
        {"type": "stream", "payload": result.model_dump()}
    )
    return result


@video_feed_router.get("/api/video-feed-settings", response_model=StreamSettings)
def get_video_settings(
    camera_manager: "CameraService" = Depends(get_camera_manager),
):
    return camera_manager.stream_settings


@video_feed_router.websocket("/ws/video-stream")
async def ws(
    websocket: WebSocket,
    stream_service: "StreamService" = Depends(get_stream_manager),
):
    """
    WebSocket endpoint for providing a video stream.

    Args:
    - websocket (WebSocket): The WebSocket connection for streaming video.
    - stream_service (StreamService): The service responsible for handling video streams.

    Exceptions:
        `WebSocketDisconnect`: Handles the case where the WebSocket connection is closed.
        `Exception`: Logs any other exceptions that occur during the video stream.
    """
    try:
        await websocket.accept()
        await stream_service.video_stream(websocket)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.log_exception("Error in video stream: ", e)


@video_feed_router.get("/api/enhancers", response_model=EnhancersResponse)
def get_frame_enhancers():
    """
    Retrieve a list of available frame enhancers.

    Returns:
        `EnhancersResponse`: A list of available frame enhancer names.
    """
    return {"enhancers": list(frame_enhancers.keys())}
