from typing import TYPE_CHECKING

from app.util.logger import Logger
from flask import Blueprint, Response, current_app

if TYPE_CHECKING:
    from app.controllers.camera_controller import CameraController

video_feed_bp = Blueprint("video_feed", __name__)
logger = Logger(__name__)


@video_feed_bp.route("/mjpg-hq")
async def video_feed_hq() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.info("Serving high quality stream.")
    await camera_manager.restart()
    response = Response(
        camera_manager.generate_high_quality_stream_jpg(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-mq")
async def video_feed_mq() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    await camera_manager.restart()
    logger.info("Serving medium quality stream.")

    response = Response(
        camera_manager.generate_medium_quality_stream_jpg(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-lq")
async def video_feed_lq() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.info("Serving low quality stream.")
    await camera_manager.restart()
    response = Response(
        camera_manager.generate_low_quality_stream_jpg(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-xhq")
async def video_feed_xhq() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.info("Serving extra high quality JPG stream.")
    await camera_manager.restart()
    response = Response(
        camera_manager.generate_robocop_vision_stream_jpg(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-xlq")
async def video_feed_xlq() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.info("Serving extra low quality JPG stream.")
    await camera_manager.restart()
    response = Response(
        camera_manager.generate_extra_low_quality_stream_jpg(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mpng-lq")
async def video_feed_png_lq() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.info("Serving low quality PNG stream.")
    await camera_manager.restart()

    if camera_manager.executor_shutdown:
        camera_manager.recreate_executor()

    response = Response(
        camera_manager.generate_low_quality_stream_png(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-hq/cat-recognize")
async def video_feed_cat_recognize() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.info("Serving cat recognize stream.")
    await camera_manager.restart()

    response = Response(
        camera_manager.generate_high_quality_stream_jpg_cat_recognize(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-hq/cat-recognize-extended")
async def video_feed_cat_extended_recognize() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.info("Serving cat recognize extended stream.")
    await camera_manager.restart()

    response = Response(
        camera_manager.generate_high_quality_stream_jpg_cat_extended_recognize(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-hq/human-face-recognize")
async def video_feed_human_recognize() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    await camera_manager.restart()
    logger.info("Serving human face recognization mode.")

    response = Response(
        camera_manager.generate_high_quality_stream_jpg_human_recognize(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-hq/human-body-recognize")
async def video_feed_human_body_recognize() -> Response:
    camera_manager: "CameraController" = current_app.config["camera_manager"]
    logger.info("Serving human body recognize stream.")
    await camera_manager.restart()

    response = Response(
        camera_manager.generate_high_quality_stream_jpg_human_full_body_recognize(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response
