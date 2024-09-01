from typing import TYPE_CHECKING
from flask import Blueprint, Response, jsonify, current_app
from app.config.logging_config import setup_logger
from time import localtime, strftime

if TYPE_CHECKING:
    from app.controllers.camera_controller import CameraController
    from app.controllers.files_controller import FilesController

video_feed_bp = Blueprint("video_feed", __name__)
logger = setup_logger(__name__)


@video_feed_bp.route("/mjpg-hq")
async def video_feed_hq() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.info("Serving high quality stream.")
    await camera_manager.start_camera_and_wait_for_flask_img()

    if camera_manager.executor_shutdown:
        camera_manager.recreate_executor()

    response = Response(
        camera_manager.generate_high_quality_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-mq")
async def video_feed_mq() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.info("Serving medium quality stream.")
    await camera_manager.start_camera_and_wait_for_flask_img()

    if camera_manager.executor_shutdown:
        camera_manager.recreate_executor()

    response = Response(
        camera_manager.generate_medium_quality_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-lq")
async def video_feed_lq() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.info("Serving low quality stream.")
    await camera_manager.start_camera_and_wait_for_flask_img()

    if camera_manager.executor_shutdown:
        camera_manager.recreate_executor()

    response = Response(
        camera_manager.generate_low_quality_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg.jpg")
async def video_feed_jpg():
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    await camera_manager.start_camera_and_wait_for_flask_img()

    if camera_manager.executor_shutdown:
        camera_manager.recreate_executor()

    response = Response(camera_manager.get_frame(), mimetype="image/jpeg")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg.png")
async def video_feed_png():
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    await camera_manager.start_camera_and_wait_for_flask_img()

    if camera_manager.executor_shutdown:
        camera_manager.recreate_executor()

    response = Response(camera_manager.get_png_frame(), mimetype="image/png")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/api/take-photo", methods=["GET"])
async def take_photo():
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    file_manager: "FilesController" = current_app.config["file_manager"]
    _time = strftime("%Y-%m-%d-%H-%M-%S", localtime())
    name = f"photo_{_time}.jpg"
    status = await camera_manager.take_photo(name, path=file_manager.user_photos_dir)
    if status:
        return jsonify({"file": name})
    return jsonify({"error": "Couldn't take photo"})


@video_feed_bp.route("/api/frame-dimensions", methods=["GET"])
async def frame_dimensions():
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    await camera_manager.start_camera_and_wait_for_flask_img()

    if camera_manager.executor_shutdown:
        camera_manager.recreate_executor()

    frame_array = camera_manager.convert_listproxy_to_array(camera_manager.flask_img)
    height, width = frame_array.shape[:2]
    return jsonify({"width": width, "height": height})


@video_feed_bp.route("/api/close-camera", methods=["GET"])
def close_camera():
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    camera_manager.camera_close()  # Close the camera
    if not camera_manager.executor_shutdown:
        camera_manager.executor.shutdown(wait=True)
        camera_manager.executor_shutdown = True  # Mark the executor as shutdown
    return jsonify({"OK": True})
