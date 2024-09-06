from time import localtime, strftime
from typing import TYPE_CHECKING, Dict, Union

from app.util.logger import Logger
from flask import Blueprint, current_app, jsonify, request

if TYPE_CHECKING:
    from app.controllers.camera_controller import CameraController
    from app.controllers.files_controller import FilesController

camera_feed_bp = Blueprint("camera_feed", __name__)
logger = Logger(__name__)


@camera_feed_bp.route("/api/take-photo", methods=["GET"])
async def take_photo():
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    file_manager: "FilesController" = current_app.config["file_manager"]
    _time = strftime("%Y-%m-%d-%H-%M-%S", localtime())
    name = f"photo_{_time}.jpg"

    await camera_manager.start_camera_and_wait_for_flask_img()
    status = await camera_manager.take_photo(name, path=file_manager.user_photos_dir)
    if status:
        return jsonify({"file": name})
    return jsonify({"error": "Couldn't take photo"})


@camera_feed_bp.route("/api/frame-dimensions", methods=["GET"])
async def frame_dimensions():
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    if camera_manager.executor_shutdown:
        camera_manager.recreate_executor()

    await camera_manager.start_camera_and_wait_for_flask_img()
    frame_array = camera_manager.convert_listproxy_to_array(camera_manager.flask_img)
    height, width = frame_array.shape[:2]
    return jsonify({"width": width, "height": height})


@camera_feed_bp.route("/api/close-camera", methods=["GET"])
def close_camera():
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.warning(f"Closing camera {camera_manager.active_clients}")
    if camera_manager.active_clients <= 1:
        camera_manager.camera_close()

    return jsonify({"OK": True})


@camera_feed_bp.route("/api/start-camera", methods=["POST"])
def start_camera():
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    payload: Union[Dict[str, int], None] = request.json
    logger.info(
        f"Opening camera, camera running: {camera_manager.camera_run} executor shutdown: {camera_manager.executor_shutdown}"
    )
    fps = (
        payload.get("fps", camera_manager.target_fps)
        if payload
        else camera_manager.target_fps
    )
    height = payload.get("height") if payload else None
    width = payload.get("width") if payload else None
    camera_manager.camera_start(fps=fps, width=width, height=height)

    return jsonify(
        {
            "width": camera_manager.frame_width,
            "height": camera_manager.frame_height,
            "fps": camera_manager.target_fps,
            "camera_running": camera_manager.camera_run,
        }
    )
