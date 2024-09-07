from typing import Any
from typing import TYPE_CHECKING, Dict, Union

from app.util.logger import Logger
from flask import Blueprint, current_app, jsonify, request, Response

if TYPE_CHECKING:
    from app.controllers.camera_controller import CameraController
    from app.controllers.files_controller import FilesController

video_feed_bp = Blueprint("video_feed", __name__)
logger = Logger(__name__)


@video_feed_bp.route("/mjpg")
async def video_feed_hq() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    file_manager: "FilesController" = current_app.config["file_manager"]
    settings = file_manager.load_settings()
    camera_manager.video_feed_detect_mode = settings.get("video_feed_detect_mode", camera_manager.video_feed_detect_mode)
    camera_manager.video_feed_enhance_mode = settings.get("video_feed_enhance_mode", camera_manager.video_feed_enhance_mode)
    camera_manager.video_feed_format = settings.get("video_feed_format", camera_manager.video_feed_format)
    camera_manager.video_feed_quality = settings.get("video_feed_quality", camera_manager.video_feed_quality)
    camera_manager.frame_width = settings.get("video_feed_width", camera_manager.frame_width)
    camera_manager.frame_height = settings.get("video_feed_height", camera_manager.frame_height)
    camera_manager.target_fps = settings.get("video_feed_fps", camera_manager.target_fps)
    logger.info(f"Serving video with quality: {camera_manager.video_feed_quality}, format: {camera_manager.video_feed_format} enhance mode: {camera_manager.video_feed_enhance_mode} detection: {camera_manager.video_feed_detect_mode}")
    await camera_manager.restart()
    response = Response(
        camera_manager.generate_video_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@video_feed_bp.route("/api/video-feed-settings", methods=["POST"])
def start_camera():
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    payload: Union[Dict[str, Any], None] = request.json
    logger.info(
        f"Updating video feed settings,executor shutdown: {camera_manager.executor_shutdown}"
    )
    if payload:
        camera_manager: "CameraController" = current_app.config["camera_manager"]
        camera_manager.video_feed_detect_mode = payload.get("video_feed_detect_mode", camera_manager.video_feed_detect_mode)
        camera_manager.video_feed_enhance_mode = payload.get("video_feed_enhance_mode", camera_manager.video_feed_enhance_mode)
        camera_manager.video_feed_format = payload.get("video_feed_format", camera_manager.video_feed_format)
        camera_manager.video_feed_quality = payload.get("video_feed_quality", camera_manager.video_feed_quality)
        camera_manager.frame_width = payload.get("video_feed_width", camera_manager.frame_width)
        camera_manager.frame_height = payload.get("video_feed_width", camera_manager.frame_height)
        camera_manager.target_fps = payload.get("video_feed_fps", camera_manager.target_fps)

    return jsonify(
        {
            "width": camera_manager.frame_width,
            "height": camera_manager.frame_height,
            "video_feed_fps": camera_manager.target_fps,
            "video_feed_detect_mode": camera_manager.video_feed_detect_mode,
            "video_feed_enhance_mode": camera_manager.video_feed_enhance_mode,
            "video_feed_quality": camera_manager.video_feed_quality,
            "video_feed_format": camera_manager.video_feed_format,

        }
    )
