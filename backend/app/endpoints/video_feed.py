from typing import TYPE_CHECKING
from flask import Blueprint, Response, jsonify, current_app
from app.config.logging_config import setup_logger

if TYPE_CHECKING:
    from app.controllers.video_stream import VideoStreamManager

video_feed_bp = Blueprint("video_feed", __name__)
logger = setup_logger(__name__)


@video_feed_bp.route("/mjpg-hq")
async def video_feed_hq() -> Response:
    video_manager: "VideoStreamManager" = current_app.config["video_manager"]
    logger.info("Serving high quality stream.")
    await video_manager.start_camera_and_wait_for_flask_img()

    if video_manager.executor_shutdown:
        video_manager.recreate_executor()

    response = Response(
        video_manager.generate_high_quality_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-mq")
async def video_feed_mq() -> Response:
    video_manager: "VideoStreamManager" = current_app.config["video_manager"]
    logger.info("Serving medium quality stream.")
    await video_manager.start_camera_and_wait_for_flask_img()

    if video_manager.executor_shutdown:
        video_manager.recreate_executor()

    response = Response(
        video_manager.generate_medium_quality_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-lq")
async def video_feed_lq() -> Response:
    video_manager: "VideoStreamManager" = current_app.config["video_manager"]
    logger.info("Serving low quality stream.")
    await video_manager.start_camera_and_wait_for_flask_img()

    if video_manager.executor_shutdown:
        video_manager.recreate_executor()

    response = Response(
        video_manager.generate_low_quality_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg.jpg")
async def video_feed_jpg():
    video_manager: "VideoStreamManager" = current_app.config["video_manager"]
    await video_manager.start_camera_and_wait_for_flask_img()

    if video_manager.executor_shutdown:
        video_manager.recreate_executor()

    response = Response(video_manager.get_frame(), mimetype="image/jpeg")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg.png")
async def video_feed_png():
    video_manager: "VideoStreamManager" = current_app.config["video_manager"]
    await video_manager.start_camera_and_wait_for_flask_img()

    if video_manager.executor_shutdown:
        video_manager.recreate_executor()

    response = Response(video_manager.get_png_frame(), mimetype="image/png")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/api/frame-dimensions", methods=["GET"])
async def frame_dimensions():
    video_manager: "VideoStreamManager" = current_app.config["video_manager"]
    await video_manager.start_camera_and_wait_for_flask_img()

    if video_manager.executor_shutdown:
        video_manager.recreate_executor()

    frame_array = video_manager.convert_listproxy_to_array(video_manager.flask_img)
    height, width = frame_array.shape[:2]
    return jsonify({"width": width, "height": height})


@video_feed_bp.route("/api/close-camera", methods=["GET"])
def close_camera():
    video_manager: "VideoStreamManager" = current_app.config["video_manager"]
    video_manager.camera_close()  # Close the camera
    if not video_manager.executor_shutdown:
        video_manager.executor.shutdown(wait=True)
        video_manager.executor_shutdown = True  # Mark the executor as shutdown
    return jsonify({"OK": True})
