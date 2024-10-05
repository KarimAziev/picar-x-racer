from typing import Callable, Optional, Sequence

import cv2
import numpy as np
from app.util.logger import Logger
from app.util.photo import height_to_width, width_to_height

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
        try:
            frame_array = frame_enhancer(frame_array)
        except Exception as err:
            logger.log_exception(
                f"Error in frame enhancer '{frame_enhancer.__name__}': ", err
            )

    frame = frame_array

    _, buffer = cv2.imencode(format, frame, params)
    return buffer.tobytes()


def resize_frame(frame: Optional[np.ndarray], width: int, height: int):
    if frame is None:
        return None
    frame = cv2.resize(frame, (width, height))
    return frame


def get_frame_size(frame: Optional[np.ndarray]):
    if frame is None:
        return (None, None)
    original_height, original_width = frame.shape[:2]
    return (original_width, original_height)


def resize_by_width_maybe(frame: np.ndarray, width: int):
    original_height, original_width = frame.shape[:2]

    if original_width == width:
        return frame

    height = width_to_height(
        width, target_width=original_width, target_height=original_height
    )

    return cv2.resize(frame, (width, height))


def resize_by_height_maybe(frame: np.ndarray, height: int):
    original_height, original_width = frame.shape[:2]

    if original_height == height:
        return frame

    width = height_to_width(
        height, target_width=original_width, target_height=original_height
    )

    return cv2.resize(frame, (width, height))
