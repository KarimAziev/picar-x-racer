import cv2
import numpy as np
from time import sleep
from typing import Generator
from util.platform_adapters import Vilib

TARGET_WIDTH = 1280
TARGET_HEIGHT = 720


def convert_listproxy_to_array(listproxy_obj):
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


def get_frame() -> bytes:
    frame_array = convert_listproxy_to_array(Vilib.flask_img)
    _, buffer = cv2.imencode(".jpg", frame_array)
    return buffer.tobytes()


def get_qrcode_pictrue() -> bytes:
    frame_array = convert_listproxy_to_array(Vilib.flask_img)
    _, buffer = cv2.imencode(".jpg", frame_array)
    return buffer.tobytes()


def get_png_frame() -> bytes:
    frame_array = convert_listproxy_to_array(Vilib.flask_img)
    _, buffer = cv2.imencode(".png", frame_array)
    return buffer.tobytes()


def get_qrcode() -> bytes:
    while Vilib.qrcode_img_encode is None:
        sleep(0.2)

    return Vilib.qrcode_img_encode


def default_gen():
    """Video streaming generator function."""
    while True:
        # start_time = time.time()
        frame = get_frame()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        sleep(0.03)
        # end_time = time.time() - start_time
        # print('flask fps:%s'%int(1/end_time))


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

        sleep(0.03)
