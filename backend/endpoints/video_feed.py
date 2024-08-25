from flask import Blueprint, Response, jsonify
from util.platform_adapters import Vilib
from util.video_utils import (
    convert_listproxy_to_array,
    generate_high_quality_stream,
    generate_low_quality_stream,
    generate_medium_quality_stream,
    get_frame,
    get_png_frame,
)

video_feed_bp = Blueprint("video_feed", __name__)


@video_feed_bp.route("/mjpg-hq")
def video_feed_hq() -> Response:
    """
    High quality video streaming route.

    Returns:
    Response
        A Flask response object containing the high quality video stream.
    """
    response = Response(
        generate_high_quality_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-mq")
def video_feed_mq() -> Response:
    """
    Medium quality video streaming route.

    Returns:
    Response
        A Flask response object containing the medium quality video stream.
    """
    response = Response(
        generate_medium_quality_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg-lq")
def video_feed_lq() -> Response:
    """
    Low quality video streaming route.

    Returns:
    Response
        A Flask response object containing the low quality video stream.
    """
    response = Response(
        generate_low_quality_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg.jpg")
def video_feed_jpg():
    """
    Single frame JPEG video streaming route.

    This can be used in the src attribute of an img tag.

    Returns:
    Response
        A Flask response object containing a single frame in JPEG format.
    """
    response = Response(get_frame(), mimetype="image/jpeg")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg.png")
def video_feed_png():
    """
    Single frame PNG video streaming route.

    This can be used in the src attribute of an img tag.

    Returns:
    Response
        A Flask response object containing a single frame in PNG format.
    """
    response = Response(get_png_frame(), mimetype="image/png")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/api/frame-dimensions", methods=["GET"])
def frame_dimensions():
    """
    Get the dimensions of the current video frame.

    Returns:
        JSON
            A JSON object containing the width and height of the video frame.
    """

    frame_array = convert_listproxy_to_array(Vilib.flask_img)
    height, width = frame_array.shape[:2]
    return jsonify({"width": width, "height": height})
