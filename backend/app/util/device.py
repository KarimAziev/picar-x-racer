from typing import Optional

import cv2
from app.util.logger import Logger

logger = Logger(__name__)


def try_video_path(path: str | int) -> Optional[cv2.VideoCapture]:
    """
    Tries to open a video capture at a specified path.

    Attempts to create and read from a video capture object using OpenCV.
    If successful, returns the video capture object; otherwise, returns None.

    Parameters:
        path: The file path or device path to the video stream.

    Returns:
        The video capture object if the path is valid and readable, otherwise None.
    """
    result: Optional[bool] = None
    cap: Optional[cv2.VideoCapture] = None

    try:
        logger.debug("Trying camera %s", path)
        cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
        result, _ = cap.read()
        if not result:
            logger.debug("Camera failed %s", path)

    except Exception as err:
        logger.debug("Camera Error: %s", err)
        if cap and cap.isOpened():
            cap.release()

    return cap if result else None
