from typing import Callable, Optional, Sequence
import cv2
import numpy as np

from app.util.logger import Logger


logger = Logger(__name__)


def encode(
    frame_array: np.ndarray,
    format=".jpg",
    params: Sequence[int] = [],
    frame_enhancer: Optional[Callable[[np.ndarray], np.ndarray]] = None,
):
    """
    Encode the frame array to the specified format.

    Args:
        frame_array (np.ndarray): Frame array to be encoded.
        format (str): Encoding format (default is ".jpg").

    Returns:
        bytes: Encoded frame as a byte array.
    """

    if frame_enhancer:
        frame_array = frame_enhancer(frame_array)

    frame = frame_array

    _, buffer = cv2.imencode(format, frame, params)
    return buffer.tobytes()


def encode_and_detect(
    frame_array: np.ndarray,
    format=".jpg",
    params: Sequence[int] = [],
    frame_enhancer: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    detection_func: Optional[Callable[[np.ndarray], np.ndarray]] = None,
):
    """
    Encode the frame array to the specified format.

    Args:
        frame_array (np.ndarray): Frame array to be encoded.
        format (str): Encoding format (default is ".jpg").

    Returns:
        bytes: Encoded frame as a byte array.
    """

    if detection_func:
        frame_array = detection_func(frame_array)

    if frame_enhancer:
        frame_array = frame_enhancer(frame_array)

    _, buffer = cv2.imencode(format, frame_array, params)
    return buffer.tobytes()
