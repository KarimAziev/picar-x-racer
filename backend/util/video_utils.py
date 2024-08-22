import cv2
import numpy as np
from time import sleep
from typing import Generator
from util.platform_adapters import Vilib

TARGET_WIDTH = 1280
TARGET_HEIGHT = 720


def convert_listproxy_to_array(listproxy_obj):
    """
    Convert a ListProxy object to a numpy array with the shape (480, 640, 3).

    Parameters:
    listproxy_obj: ListProxy
        The ListProxy object to be converted.

    Returns:
    np.ndarray
        A numpy array representation of the ListProxy object.
    """
    return np.array(listproxy_obj, dtype=np.uint8).reshape((480, 640, 3))


def enhance_frame(frame: np.ndarray) -> np.ndarray:
    """
    Enhance the input video frame by denoising and adjusting its contrast.

    Parameters:
    frame: np.ndarray
        The input video frame in BGR format.

    Returns:
    np.ndarray
        The enhanced video frame.
    """
    denoised_frame = cv2.fastNlMeansDenoisingColored(frame, None, 10, 10, 7, 21)

    lab = cv2.cvtColor(denoised_frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    final_frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    return final_frame


def get_frame() -> bytes:
    """
    Get the current video frame encoded as a JPEG byte array.

    Returns:
    bytes
        The JPEG encoded byte array of the current video frame.
    """
    frame_array = convert_listproxy_to_array(Vilib.flask_img)
    _, buffer = cv2.imencode(".jpg", frame_array)
    return buffer.tobytes()


def get_qrcode_pictrue() -> bytes:
    """
    Get the current QR code picture frame encoded as a JPEG byte array.

    Returns:
    bytes
        The JPEG encoded byte array of the current QR code picture frame.
    """
    frame_array = convert_listproxy_to_array(Vilib.flask_img)
    _, buffer = cv2.imencode(".jpg", frame_array)
    return buffer.tobytes()


def get_png_frame() -> bytes:
    """
    Get the current video frame encoded as a PNG byte array.

    Returns:
    bytes
        The PNG encoded byte array of the current video frame.
    """
    frame_array = convert_listproxy_to_array(Vilib.flask_img)
    _, buffer = cv2.imencode(".png", frame_array)
    return buffer.tobytes()


def get_qrcode() -> bytes:
    """
    Get the current QR code image once it is available.

    Returns:
    bytes
        The byte array of the encoded QR code image.
    """
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


def generate_video_stream() -> Generator[bytes, None, None]:
    """
    Video streaming generator function that yields JPEG encoded frames.

    Yields:
    Generator[bytes, None, None]
        A generator that yields a sequence of JPEG encoded frames.
    """
    while True:
        frame = get_frame()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        sleep(0.03)


def generate_high_quality_stream() -> Generator[bytes, None, None]:
    """
    High quality video streaming generator function that yields enhanced, resized, and JPEG encoded frames.

    Yields:
    Generator[bytes, None, None]
        A generator that yields a sequence of high quality JPEG encoded frames.
    """
    while True:
        frame_array = convert_listproxy_to_array(Vilib.flask_img)
        enhanced_frame = enhance_frame(frame_array)
        resized_frame = cv2.resize(
            enhanced_frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_CUBIC
        )
        _, buffer = cv2.imencode(".jpg", resized_frame)
        frame = buffer.tobytes()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        sleep(0.03)


def generate_medium_quality_stream() -> Generator[bytes, None, None]:
    """
    Medium quality video streaming generator function that yields resized and JPEG encoded frames.

    Yields:
    Generator[bytes, None, None]
        A generator that yields a sequence of medium quality JPEG encoded frames.
    """
    while True:
        frame_array = convert_listproxy_to_array(Vilib.flask_img)
        resized_frame = cv2.resize(
            frame_array, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_CUBIC
        )
        _, buffer = cv2.imencode(".jpg", resized_frame)
        frame = buffer.tobytes()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        sleep(0.03)


def generate_low_quality_stream() -> Generator[bytes, None, None]:
    """
    Low quality video streaming generator function that yields resized and PNG encoded frames.

    Yields:
    Generator[bytes, None, None]
        A generator that yields a sequence of low quality PNG encoded frames.
    """
    while True:
        frame_array = convert_listproxy_to_array(Vilib.flask_img)
        resized_frame = cv2.resize(
            frame_array, (640, 360), interpolation=cv2.INTER_LINEAR
        )
        _, buffer = cv2.imencode(".png", resized_frame)
        frame = buffer.tobytes()
        yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        sleep(0.03)
