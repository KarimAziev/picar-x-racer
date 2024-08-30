from concurrent.futures import ProcessPoolExecutor
from typing import Generator

import cv2
import numpy as np
from app.config.logging_config import setup_logger

from app.util.platform_adapters import Vilib

logger = setup_logger(__name__)

# Constants for target width and height of video streams
TARGET_WIDTH = 640
TARGET_HEIGHT = 480

executor = ProcessPoolExecutor(max_workers=4)


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

    np_array = np.array(listproxy_obj, dtype=np.uint8)

    return np_array


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


def resize_and_encode(
    frame: np.ndarray, width: int, height: int, format=".jpg", quality=90
):
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


def encode(frame_array: np.ndarray, format=".jpg"):
    """
    Encode frame.

    Parameters:
        frame (np.ndarray): The input frame to resize and encode.
        format (str): The encoding format, e.g., '.jpg' or '.png'. Default is '.jpg'.

    Returns:
        bytes: The encoded frame.
    """
    _, buffer = cv2.imencode(format, frame_array)
    return buffer.tobytes()


def async_generate_video_stream(width: int, height: int, format=".jpg", quality=90):
    """
    Asynchronously generate a video stream encoded in the specified format and quality.
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


def async_generate_video_stream_no_transform(format=".png"):
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
            frame_array = convert_listproxy_to_array(Vilib.flask_img)
            future = executor.submit(encode, frame_array, format)
            encoded_frame = future.result()
            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded_frame + b"\r\n"
            )
        else:
            logger.warning("Vilib.flask_img is None, skipping frame.")


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
    return async_generate_video_stream_no_transform(".jpg")


def generate_low_quality_stream() -> Generator[bytes, None, None]:
    """
    Generate a low-quality video stream.

    Returns:
        Generator[bytes, None, None]: A generator yielding low-quality video frames.
    """
    return async_generate_video_stream_no_transform(".png")