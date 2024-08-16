from flask import Blueprint, Response
from util.video_utils import gen, get_frame, get_png_frame

video_feed_bp = Blueprint("video_feed", __name__)


@video_feed_bp.route("/mjpg")
def video_feed() -> Response:
    """
    Video streaming route.
    """
    response = Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg.jpg")
def video_feed_jpg():
    """Video streaming route. Put this in the src attribute of an img tag."""
    response = Response(get_frame(), mimetype="image/jpeg")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


@video_feed_bp.route("/mjpg.png")
def video_feed_png():
    """Video streaming route. Put this in the src attribute of an img tag."""
    response = Response(get_png_frame(), mimetype="image/png")
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response
