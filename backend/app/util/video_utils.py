import collections
from typing import Callable, Optional, Sequence, Union

import cv2
import numpy as np
from app.core.logger import Logger
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


def resize_to_fixed_height(frame: np.ndarray, base_size=256):
    """
    Resizes the input frame to a specified base height while maintaining aspect ratio.

    This function takes a frame in the form of a NumPy array and resizes it to a
    given base height (`base_size`). The new width is calculated proportionally
    based on the original aspect ratio, using a function `height_to_width` to
    ensure the aspect ratio is preserved. The resulting resized frame dimensions may
    also optionally be rounded up to the nearest multiple of a given value (e.g., 32).

    Args:
        frame (np.ndarray): The input image or video frame to be resized.
        base_size (int, optional): The height to resize the frame to. The width
                                   will be calculated according to the original
                                   aspect ratio.

    Returns:
        tuple: A tuple consisting of:
            - frame (np.ndarray): The resized frame as an image.
            - original_width (int): The original width of the input frame.
            - original_height (int): The original height of the input frame.
            - resized_width (int): The new width of the resized frame.
            - resized_height (int): The new height of the resized frame (equals `base_size`).

    Example:
        >>> import numpy as np
        >>> frame = np.random.rand(640, 480, 3)  # Assuming an example frame
        >>> resized_frame, orig_w, orig_h, new_w, new_h = resize_to_fixed_height(frame, base_size=192)
        >>> print(f"Original size: {orig_w}x{orig_h}")
        >>> print(f"Resized size: {new_w}x{new_h}")
    """
    original_height, original_width = frame.shape[:2]
    resized_height = base_size
    resized_width = height_to_width(
        base_size,
        target_width=original_width,
        target_height=original_height,
        round_up_to_multiple=32,
    )
    frame = cv2.resize(frame, (resized_width, resized_height))
    return (frame, original_width, original_height, resized_width, resized_height)


def calc_fps(
    frame_timestamps: Union[collections.deque, list[float]], round_result: bool = False
) -> Optional[Union[float, int]]:
    """
    Calculate frames per second (FPS) based on a list or deque of frame timestamps.

    This function computes the average frame rate by determining the
    difference between consecutive timestamps in the provided `frame_timestamps`.
    The FPS is calculated as the reciprocal of the average time difference between frames.

    Args:
        `frame_timestamps`: A deque or list of timestamps (in seconds) representing the time
            when each frame was recorded. Must contain at least two timestamps.

        `round_result`: If True, the FPS result will be rounded to the nearest integer.
            Defaults to False.

    Returns:
            The calculated FPS as a float or an integer if `round_result` is True.
            Returns None if the average time difference is zero or the input is insufficient
            (less than two timestamps).

    Example:
        >>> from collections import deque
        >>> timestamps = deque([0.0, 0.033, 0.067, 0.100])
        >>> calc_fps(timestamps)
        30.303030303030305

        >>> calc_fps(timestamps, round_result=True)
        30

    Notes:
        - If `frame_timestamps` contains fewer than two timestamps, the function
          immediately returns None as it cannot calculate FPS.
        - The function makes no assumptions about the uniformity of time intervals
          between frames; it computes the average difference over all available
          timestamps.

    """
    if len(frame_timestamps) >= 2:
        time_diffs = [
            t2 - t1 for t1, t2 in zip(frame_timestamps, list(frame_timestamps)[1:])
        ]
        avg_time_diff = sum(time_diffs) / len(time_diffs)

        fps = 1.0 / avg_time_diff if avg_time_diff > 0 else None
        if fps is None:
            return None

        return round(fps) if round_result else int(fps * 10) / 10
