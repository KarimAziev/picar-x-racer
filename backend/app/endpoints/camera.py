from time import localtime, strftime
from typing import TYPE_CHECKING

import numpy as np
from app.util.logger import Logger
from flask import Blueprint, current_app, jsonify

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
    frame_array = np.array(camera_manager.flask_img, dtype=np.uint8)
    height, width = frame_array.shape[:2]
    return jsonify({"width": width, "height": height})


@camera_feed_bp.route("/api/close-camera", methods=["GET"])
def close_camera():
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.warning(f"Closing camera {camera_manager.active_clients}")
    if camera_manager.active_clients <= 1:
        camera_manager.camera_close()

    return jsonify({"OK": True})
