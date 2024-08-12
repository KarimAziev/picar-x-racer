from flask import Blueprint, Response
import cv2
import numpy as np
from vilib import Vilib
from time import sleep

video_feed_bp = Blueprint("video_feed", __name__)


TARGET_WIDTH = 1280
TARGET_HEIGHT = 720


def convert_listproxy_to_array(listproxy_obj):
    return np.array(listproxy_obj, dtype=np.uint8).reshape((480, 640, 3))


def gen():
    while True:
        # Convert the ListProxy object to a Numpy array with original dimensions
        frame_array = convert_listproxy_to_array(Vilib.flask_img)

        # Resize the frame to the target resolution using high-quality interpolation
        resized_frame = cv2.resize(
            frame_array, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_CUBIC
        )

        _, buffer = cv2.imencode(".jpg", resized_frame)
        frame = buffer.tobytes()

        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

        sleep(0.1)


@video_feed_bp.route("/mjpg")
def video_feed():
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")
