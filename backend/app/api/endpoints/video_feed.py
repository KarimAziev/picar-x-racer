from typing import TYPE_CHECKING

from app.api.deps import get_camera_manager, get_detection_manager, get_stream_manager
from app.schemas.settings import VideoFeedSettings, VideoFeedUpdateSettings
from app.util.logger import Logger
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from app.services.camera_service import CameraService
    from app.services.detection_service import DetectionService
    from app.services.stream_service import StreamService

logger = Logger(__name__)


video_feed_router = APIRouter()


@video_feed_router.post("/api/video-feed-settings", response_model=VideoFeedSettings)
def update_video_feed_settings(
    payload: VideoFeedUpdateSettings,
    camera_manager: "CameraService" = Depends(get_camera_manager),
    detection_manager: "DetectionService" = Depends(get_detection_manager),
):
    logger.info(f"Updating video feed settings: {payload}")
    if payload:
        for key, value in payload.model_dump(exclude_unset=True).items():
            if key is "video_feed_detect_mode":
                detection_manager.video_feed_detect_mode = value
                if (
                    detection_manager.video_feed_detect_mode
                    and camera_manager.camera_run
                ):
                    detection_manager.start_detection_process()

            elif hasattr(camera_manager, key):
                setattr(camera_manager, key, value)

    return {
        "video_feed_width": camera_manager.video_feed_width,
        "video_feed_height": camera_manager.video_feed_width,
        "video_feed_fps": camera_manager.video_feed_fps,
        "video_feed_detect_mode": detection_manager.video_feed_detect_mode,
        "video_feed_enhance_mode": camera_manager.video_feed_enhance_mode,
        "video_feed_quality": camera_manager.video_feed_quality,
        "video_feed_format": camera_manager.video_feed_format,
    }


@video_feed_router.get("/api/video-feed-settings", response_model=VideoFeedSettings)
def get_camera_settings(
    camera_manager: "CameraService" = Depends(get_camera_manager),
    detection_manager: "DetectionService" = Depends(get_detection_manager),
):
    return {
        "video_feed_width": camera_manager.video_feed_width,
        "video_feed_height": camera_manager.video_feed_width,
        "video_feed_fps": camera_manager.video_feed_fps,
        "video_feed_detect_mode": detection_manager.video_feed_detect_mode,
        "video_feed_enhance_mode": camera_manager.video_feed_enhance_mode,
        "video_feed_quality": camera_manager.video_feed_quality,
        "video_feed_format": camera_manager.video_feed_format,
    }


@video_feed_router.websocket("/ws/video-stream")
async def ws(
    websocket: WebSocket,
    stream_service: "StreamService" = Depends(get_stream_manager),
):
    await websocket.accept()

    try:
        await stream_service.video_stream(websocket)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Error in video stream: {e}")
