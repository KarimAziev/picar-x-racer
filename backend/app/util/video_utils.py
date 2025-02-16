import collections
from typing import Callable, List, Literal, Optional, Sequence, Tuple, Union, overload

import cv2
import numpy as np
from app.core.logger import Logger
from app.util.photo import height_to_width, width_to_height

logger = Logger(__name__)


def encode(
    frame: np.ndarray,
    format=".jpg",
    params: Sequence[int] = [],
    frame_enhancer: Optional[Callable[[np.ndarray], np.ndarray]] = None,
):
    """
    Encode the frame array to the specified format.
    If the frame is 16-bit (for instance from a "RGB161616" or "BGR161616" format),
    converts it to 8-bit before encoding.

    Returns:
        bytes: Encoded frame as a byte array.
    """

    if frame_enhancer:
        try:
            frame = frame_enhancer(frame)
        except Exception:
            logger.error(
                f"Error in frame enhancer '{frame_enhancer.__name__}'", exc_info=True
            )

    if frame.dtype == np.uint16:
        # Shift right 8 bits;
        frame = (frame >> 8).astype(np.uint8)

    # if frame.ndim == 2:
    #     channels = 1
    # elif frame.ndim == 3:
    #     channels = frame.shape[2]
    # else:
    #     raise ValueError("Frame has an unexpected number of dimensions.")

    # if channels not in (1, 3, 4):
    #     raise ValueError(f"After conversion, invalid number of channels: {channels}")

    success, buffer = cv2.imencode(format, frame, params or [])
    if not success:
        raise ValueError("cv2.imencode failed to encode the frame.")
    return buffer.tobytes()


@overload
def resize_frame(frame: None, width: int, height: int) -> None: ...


@overload
def resize_frame(frame: np.ndarray, width: int, height: int) -> np.ndarray: ...
def resize_frame(
    frame: Optional[np.ndarray], width: int, height: int
) -> Optional[np.ndarray]:
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


@overload
def calc_fps(
    frame_timestamps: Union[collections.deque, List[float]],
    *,
    round_result: Literal[True],
) -> Optional[int]: ...


@overload
def calc_fps(
    frame_timestamps: Union[collections.deque, List[float]],
    *,
    round_result: Literal[False] = False,
) -> Optional[float]: ...
def calc_fps(
    frame_timestamps: Union[collections.deque, List[float]],
    *,
    round_result: bool = False,
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


def letterbox(
    image: np.ndarray,
    expected_w: int,
    expected_h: int,
    color: Tuple[int, int, int] = (0, 0, 0),
) -> np.ndarray:
    """
    Resize image to fit within (expected_w, expected_h) while preserving aspect ratio,
    and pad the rest with a given color.

    Args:
        image: The source image.
        expected_w: Target width.
        expected_h: Target height.
        color: Padding color.

    Returns:
        The padded image with shape (expected_h, expected_w, channels).
    """
    original_h, original_w = image.shape[:2]

    scale = min(expected_w / original_w, expected_h / original_h)
    new_w = int(original_w * scale)
    new_h = int(original_h * scale)
    resized = cv2.resize(image, (new_w, new_h))

    pad_w = expected_w - new_w
    pad_h = expected_h - new_h

    pad_left = pad_w // 2
    pad_right = pad_w - pad_left
    pad_top = pad_h // 2
    pad_bottom = pad_h - pad_top

    padded = cv2.copyMakeBorder(
        resized,
        pad_top,
        pad_bottom,
        pad_left,
        pad_right,
        borderType=cv2.BORDER_CONSTANT,
        value=color,
    )
    return padded
