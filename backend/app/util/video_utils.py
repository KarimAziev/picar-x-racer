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
        try:
            frame_array = frame_enhancer(frame_array)
        except Exception as err:
            logger.log_exception(
                f"Error in frame enhancer '{frame_enhancer.__name__}': ", err
            )

    frame = frame_array

    _, buffer = cv2.imencode(format, frame, params)
    return buffer.tobytes()
