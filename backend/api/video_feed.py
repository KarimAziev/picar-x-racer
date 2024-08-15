from flask import Blueprint, Response
import cv2
import numpy as np
from vilib import Vilib
from time import sleep
from typing import Generator, Any

video_feed_bp = Blueprint("video_feed", __name__)

TARGET_WIDTH = 1280
TARGET_HEIGHT = 720


def convert_listproxy_to_array(listproxy_obj: Any) -> np.ndarray:
    return np.array(listproxy_obj, dtype=np.uint8).reshape((480, 640, 3))


def enhance_frame(frame: np.ndarray) -> np.ndarray:
    denoised_frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)

    lab = cv2.cvtColor(denoised_frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    final_frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    return final_frame


def gen() -> Generator[bytes, None, None]:
    while True:
        # Convert the ListProxy object to a Numpy array with original dimensions
        frame_array = convert_listproxy_to_array(Vilib.flask_img)
        enhanced_frame = enhance_frame(frame_array)

        # Resize the frame to the target resolution using high-quality interpolation
        resized_frame = cv2.resize(
            enhanced_frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_CUBIC
        )

        _, buffer = cv2.imencode(".jpg", resized_frame)
        frame = buffer.tobytes()

        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

        sleep(0.1)


@video_feed_bp.route("/mjpg")
def video_feed() -> Response:
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")
