from typing import TYPE_CHECKING, Any, Dict, Union

from app.util.logger import Logger
from flask import Blueprint, current_app, jsonify, request

if TYPE_CHECKING:
    from app.controllers.camera_controller import CameraController

video_feed_bp = Blueprint("video_feed", __name__)
logger = Logger(__name__)


@video_feed_bp.route("/api/video-feed-settings", methods=["POST"])
def start_camera():
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    payload: Union[Dict[str, Any], None] = request.json
    logger.info(f"Updating video feed settings: {payload}")
    if payload:
        camera_manager: "CameraController" = current_app.config["camera_manager"]
        camera_manager.video_feed_detect_mode = payload.get(
            "video_feed_detect_mode", camera_manager.video_feed_detect_mode
        )
        camera_manager.video_feed_enhance_mode = payload.get(
            "video_feed_enhance_mode", camera_manager.video_feed_enhance_mode
        )
        camera_manager.video_feed_format = payload.get(
            "video_feed_format", camera_manager.video_feed_format
        )
        camera_manager.video_feed_quality = payload.get(
            "video_feed_quality", camera_manager.video_feed_quality
        )
        camera_manager.frame_width = payload.get(
            "video_feed_width", camera_manager.frame_width
        )
        camera_manager.frame_height = payload.get(
            "video_feed_width", camera_manager.frame_height
        )
        camera_manager.target_fps = payload.get(
            "video_feed_fps", camera_manager.target_fps
        )

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


@video_feed_bp.route("/api/video-feed-settings", methods=["GET"])
def get_camera_settings():
    camera_manager: "CameraController" = current_app.config["camera_manager"]

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
