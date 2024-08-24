import cv2
import numpy as np
from time import sleep
from typing import Generator
from util.platform_adapters import Vilib
from colorlog import ColoredFormatter
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = ColoredFormatter(
    "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt=None,
    reset=True,
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "red,bg_white",
    },
    secondary_log_colors={},
    style="%",
)
ch.setFormatter(formatter)
logger.addHandler(ch)

# Constants for target width and height of video streams
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720

# Thread pool executor for handling asynchronous tasks
executor = ThreadPoolExecutor(max_workers=4)


def convert_listproxy_to_array(listproxy_obj):
    """
    Convert a ListProxy object to a NumPy array.

    Parameters:
        listproxy_obj (ListProxy): The ListProxy object to convert.

    Returns:
        np.ndarray: The converted NumPy array.
    """
    if listproxy_obj is None:
        logger.error("ListProxy object is None")
        raise ValueError("ListProxy object is None")
    return np.array(listproxy_obj, dtype=np.uint8).reshape((480, 640, 3))


def enhance_frame(frame: np.ndarray) -> np.ndarray:
    """
    Enhance the input video frame by denoising and applying CLAHE.

    Parameters:
        frame (np.ndarray): The input frame to enhance.

    Returns:
        np.ndarray: The enhanced frame.
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
    Get the current frame as a JPEG-encoded byte array.

    Returns:
        bytes: The encoded frame.
    """
    if Vilib.flask_img is None:
        logger.error("Vilib.flask_img is None")
        raise ValueError("Vilib.flask_img is None")
    frame_array = convert_listproxy_to_array(Vilib.flask_img)
    _, buffer = cv2.imencode(".jpg", frame_array)
    return buffer.tobytes()


def get_qrcode_pictrue() -> bytes:
    """
    Get the current QR code picture as a JPEG-encoded byte array.

    Returns:
        bytes: The encoded QR code picture.
    """
    if Vilib.flask_img is None:
        logger.error("Vilib.flask_img is None")
        raise ValueError("Vilib.flask_img is None")

    frame_array = convert_listproxy_to_array(Vilib.flask_img)
    _, buffer = cv2.imencode(".jpg", frame_array)
    return buffer.tobytes()


def get_png_frame() -> bytes:
    """
    Get the current frame as a PNG-encoded byte array.

    Returns:
        bytes: The encoded frame.
    """
    if Vilib.flask_img is None:
        logger.error("Vilib.flask_img is None")
        raise ValueError("Vilib.flask_img is None")

    frame_array = convert_listproxy_to_array(Vilib.flask_img)
    _, buffer = cv2.imencode(".png", frame_array)
    return buffer.tobytes()


def get_qrcode() -> bytes:
    """
    Get the encoded QR code image as a byte array. Waits until the QR code
    image is available.

    Returns:
        bytes: The QR code image in encoded bytes.
    """
    while Vilib.qrcode_img_encode is None:
        sleep(0.2)
    return Vilib.qrcode_img_encode


def resize_and_encode(frame, width, height, format=".jpg", quality=90):
    """
    Resize and encode frame.

    Parameters:
        frame (np.ndarray): The input frame to resize and encode.
        width (int): The target width of the frame.
        height (int): The target height of the frame.
        format (str): The encoding format, e.g., '.jpg' or '.png'. Default is '.jpg'.
        quality (int): The encoding quality (only applies to JPEG). Default is 90.

    Returns:
        bytes: The encoded frame.
    """
    resized_frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_CUBIC)
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality] if format == ".jpg" else []
    _, buffer = cv2.imencode(format, resized_frame, encode_params)
    return buffer.tobytes()


def async_generate_video_stream(width: int, height: int, format=".jpg", quality=90):
    """
    Asynchronously generate a video stream encoded in the specified format and quality.

    Parameters:
        width (int): Target width for the encoded frames.
        height (int): Target height for the encoded frames.
        format (str): The encoding format ('jpg' or 'png'). Default is '.jpg'.
        quality (int): The encoding quality (applicable only for JPEG). Default is 90.

    Yields:
        bytes: Encoded frames in byte-string format ready for streaming.
    """
    while True:
        if Vilib.flask_img is not None:
            frame = convert_listproxy_to_array(Vilib.flask_img)
            future = executor.submit(
                resize_and_encode, frame, width, height, format, quality
            )
            encoded_frame = future.result()
            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded_frame + b"\r\n"
            )
        else:
            logger.warning("Vilib.flask_img is None, skipping frame.")
        sleep(0.05)


def generate_high_quality_stream() -> Generator[bytes, None, None]:
    """
    Generate a high-quality video stream.

    Returns:
        Generator[bytes, None, None]: A generator yielding high-quality video frames.
    """
    return async_generate_video_stream(TARGET_WIDTH, TARGET_HEIGHT)


def generate_medium_quality_stream() -> Generator[bytes, None, None]:
    """
    Generate a medium-quality video stream.

    Returns:
        Generator[bytes, None, None]: A generator yielding medium-quality video frames.
    """
    return async_generate_video_stream(TARGET_WIDTH, TARGET_HEIGHT, quality=75)


def generate_low_quality_stream() -> Generator[bytes, None, None]:
    """
    Generate a low-quality video stream.

    Returns:
        Generator[bytes, None, None]: A generator yielding low-quality video frames.
    """
    return async_generate_video_stream(640, 360, quality=50)
