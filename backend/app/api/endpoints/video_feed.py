import asyncio
from typing import TYPE_CHECKING

from app.api.deps import get_camera_manager, get_detection_manager, get_stream_manager
from app.schemas.settings import VideoFeedSettings, VideoFeedUpdateSettings
from app.services.connection_service import ConnectionService
from app.util.logger import Logger
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

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
    """
    Update the video feed settings of the application.

    Args:
    - payload (VideoFeedUpdateSettings): The new settings to apply to the video feed.
    - camera_manager (CameraService): The camera service for managing the camera settings.
    - detection_manager (DetectionService): The detection service for managing the detection settings.

    Returns:
        `VideoFeedSettings`: The updated settings of the video feed.
    """

    if payload:
        if payload.video_feed_confidence:
            detection_manager.video_feed_confidence = payload.video_feed_confidence

        dict_data = payload.model_dump(exclude_unset=True)
        logger.info(f"Updating feed settings: {dict_data}")
        current_width = camera_manager.video_feed_width
        current_height = camera_manager.video_feed_height
        object_detection_size = camera_manager.video_feed_model_img_size
        keys_to_restart = {
            "video_feed_device",
            "video_feed_width",
            "video_feed_height",
            "video_feed_fps",
            "video_feed_pixel_format",
            "video_feed_model_img_size",
        }

        should_restart_detection_process = None

        should_restart_camera = False
        if dict_data.get('video_feed_object_detection') == False:
            detection_manager.stop_detection_process()

        if dict_data.get('video_feed_object_detection') == True:
            detection_manager.video_feed_object_detection = True

        for key, value in dict_data.items():
            if key in keys_to_restart:
                should_restart_camera = True

            if key is "video_feed_detect_mode":
                detection_manager.video_feed_detect_mode = value
            elif key is "video_feed_object_detection":
                detection_manager.video_feed_object_detection = value
            elif hasattr(camera_manager, key):
                logger.debug(f"Setting camera_manager {key} to {value}")
                setattr(camera_manager, key, value)

        if should_restart_camera:
            camera_manager.restart_camera()

        should_restart_detection_process = (
            current_width != camera_manager.video_feed_width
            and current_height != camera_manager.video_feed_height
            or object_detection_size != camera_manager.video_feed_model_img_size
        )

        if dict_data.get('video_feed_object_detection') == False:
            detection_manager.stop_detection_process()
        elif (
            should_restart_detection_process
            and detection_manager.detection_process
            and detection_manager.detection_process.is_alive()
        ):
            detection_manager.restart_detection_process()
        elif (
            detection_manager.video_feed_object_detection
            and detection_manager.video_feed_detect_mode
            and (
                detection_manager.detection_process is None
                or not detection_manager.detection_process.is_alive()
                and not detection_manager.loading
            )
        ):
            detection_manager.start_detection_process()

    return {
        "video_feed_detect_mode": detection_manager.video_feed_detect_mode,
        "video_feed_confidence": detection_manager.video_feed_confidence,
        "video_feed_object_detection": detection_manager.video_feed_object_detection,
        "video_feed_model_img_size": camera_manager.video_feed_model_img_size,
        "video_feed_width": camera_manager.video_feed_width,
        "video_feed_height": camera_manager.video_feed_height,
        "video_feed_fps": camera_manager.video_feed_fps,
        "video_feed_enhance_mode": camera_manager.video_feed_enhance_mode,
        "video_feed_quality": camera_manager.video_feed_quality,
        "video_feed_format": camera_manager.video_feed_format,
        "video_feed_record": camera_manager.video_feed_record,
        "video_feed_device": camera_manager.video_feed_device,
        "video_feed_pixel_format": camera_manager.video_feed_pixel_format,
    }


@video_feed_router.get("/api/video-feed-settings", response_model=VideoFeedSettings)
def get_camera_settings(
    camera_manager: "CameraService" = Depends(get_camera_manager),
    detection_manager: "DetectionService" = Depends(get_detection_manager),
):
    """
    Retrieve the current video feed settings of the application.

    Args:
    - camera_manager (CameraService): The camera service for managing the camera settings.
    - detection_manager (DetectionService): The detection service for managing the detection settings.

    Returns:
        `VideoFeedSettings`: The current settings of the video feed.
    """

    return {
        "video_feed_detect_mode": detection_manager.video_feed_detect_mode,
        "video_feed_object_detection": detection_manager.video_feed_object_detection,
        "video_feed_confidence": detection_manager.video_feed_confidence,
        "video_feed_model_img_size": camera_manager.video_feed_model_img_size,
        "video_feed_width": camera_manager.video_feed_width,
        "video_feed_height": camera_manager.video_feed_height,
        "video_feed_fps": camera_manager.video_feed_fps,
        "video_feed_enhance_mode": camera_manager.video_feed_enhance_mode,
        "video_feed_quality": camera_manager.video_feed_quality,
        "video_feed_format": camera_manager.video_feed_format,
        "video_feed_record": camera_manager.video_feed_record,
        "video_feed_device": camera_manager.video_feed_device,
        "video_feed_pixel_format": camera_manager.video_feed_pixel_format,
    }


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


@video_feed_router.websocket("/ws/object-detection")
async def object_detection(
    websocket: WebSocket,
    detection_service: "DetectionService" = Depends(get_detection_manager),
):
    connection_manager: "ConnectionService" = websocket.app.state.detection_notifier
    try:
        await connection_manager.connect(websocket)
        while True:
            if websocket.application_state == WebSocketState.DISCONNECTED:
                connection_manager.disconnect(websocket)
                break
            elif detection_service.stop_event.is_set():
                break
            else:
                await asyncio.to_thread(detection_service.get_detection)
                if websocket.application_state == WebSocketState.DISCONNECTED:
                    connection_manager.disconnect(websocket)
                    break
                else:
                    await connection_manager.broadcast()
    except WebSocketDisconnect:
        logger.info("Detection WebSocket Disconnected")
    except asyncio.CancelledError:
        logger.info("Gracefully shutting down Detection WebSocket connection")
    except KeyboardInterrupt:
        logger.info("Detection WebSocket interrupted")
    finally:
        if websocket.application_state == WebSocketState.CONNECTED:
            await websocket.close()
        connection_manager.disconnect(websocket)
