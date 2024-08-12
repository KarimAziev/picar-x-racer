from flask import Blueprint, Response
import cv2
import numpy as np
from vilib import Vilib
from time import sleep

video_feed_bp = Blueprint("video_feed", __name__)


def convert_listproxy_to_array(listproxy_obj):
    return np.array(listproxy_obj, dtype=np.uint8).reshape((480, 640, 3))


def gen():
    while True:
        frame_array = convert_listproxy_to_array(Vilib.flask_img)
        _, buffer = cv2.imencode(".jpg", frame_array)
        frame = buffer.tobytes()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        sleep(0.1)


@video_feed_bp.route("/mjpg")
def video_feed():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")
