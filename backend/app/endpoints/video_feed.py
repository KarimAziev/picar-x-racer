from typing import TYPE_CHECKING, Union

from app.deps import get_camera_manager, get_detection_manager, get_stream_manager
from app.util.logger import Logger
from fastapi import APIRouter, Depends, FastAPI, WebSocket
from fastapi.responses import JSONResponse
from pydantic import BaseModel

if TYPE_CHECKING:
    from app.controllers.camera_controller import CameraController
    from app.controllers.detection_controller import DetectionController
    from app.controllers.stream_controller import StreamController

logger = Logger(__name__)

app = FastAPI()
video_feed_router = APIRouter()


class VideoFeedSettings(BaseModel):
    video_feed_detect_mode: Union[str, None] = None
    video_feed_enhance_mode: Union[str, None] = None
    video_feed_format: Union[str, None] = None
    video_feed_quality: Union[int, None] = None
    video_feed_width: Union[int, None] = None
    video_feed_height: Union[int, None] = None
    video_feed_fps: Union[int, None] = None


@video_feed_router.post("/api/video-feed-settings")
async def update_video_feed_settings(
    payload: VideoFeedSettings,
    camera_manager: "CameraController" = Depends(get_camera_manager),
    detection_manager: "DetectionController" = Depends(get_detection_manager),
):
    logger.info(f"Updating video feed settings: {payload}")
    if payload:
        detection_manager.video_feed_detect_mode = payload.video_feed_detect_mode
        camera_manager.video_feed_enhance_mode = payload.video_feed_enhance_mode

        if payload.video_feed_format is not None:
            camera_manager.video_feed_format = payload.video_feed_format
        if payload.video_feed_quality is not None:
            camera_manager.video_feed_quality = payload.video_feed_quality
        if payload.video_feed_width is not None:
            camera_manager.frame_width = payload.video_feed_width
        if payload.video_feed_height is not None:
            camera_manager.frame_height = payload.video_feed_height
        if payload.video_feed_fps is not None:
            camera_manager.target_fps = payload.video_feed_fps

    return JSONResponse(
        content={
            "width": camera_manager.frame_width,
            "height": camera_manager.frame_height,
            "video_feed_fps": camera_manager.target_fps,
            "video_feed_detect_mode": detection_manager.video_feed_detect_mode,
            "video_feed_enhance_mode": camera_manager.video_feed_enhance_mode,
            "video_feed_quality": camera_manager.video_feed_quality,
            "video_feed_format": camera_manager.video_feed_format,
        }
    )


@video_feed_router.get("/api/video-feed-settings")
async def get_camera_settings(
    camera_manager: "CameraController" = Depends(get_camera_manager),
    detection_manager: "DetectionController" = Depends(get_detection_manager),
):
    return JSONResponse(
        content={
            "width": camera_manager.frame_width,
            "height": camera_manager.frame_height,
            "video_feed_fps": camera_manager.target_fps,
            "video_feed_detect_mode": detection_manager.video_feed_detect_mode,
            "video_feed_enhance_mode": camera_manager.video_feed_enhance_mode,
            "video_feed_quality": camera_manager.video_feed_quality,
            "video_feed_format": camera_manager.video_feed_format,
        }
    )


@video_feed_router.websocket("/ws/video-stream")
async def ws(
    websocket: WebSocket,
    stream_controller: "StreamController" = Depends(get_stream_manager),
):

    await websocket.accept()
    await stream_controller.video_stream(websocket)
