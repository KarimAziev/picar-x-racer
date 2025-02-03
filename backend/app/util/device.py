from typing import TYPE_CHECKING, Optional, Union

import cv2
from app.core.logger import Logger

logger = Logger(__name__)

if TYPE_CHECKING:
    from cv2 import VideoCaptureAPIs


def try_video_path(
    path: Union[str, int],
    backend: Optional["VideoCaptureAPIs"] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    fps: Optional[float] = None,
    pixel_format: Optional[str] = None,
) -> Optional[cv2.VideoCapture]:
    """
    Tries to open a video capture at a specified path.

    Attempts to create and read from a video capture object using OpenCV.
    If successful, returns the video capture object; otherwise, returns None.

    Args:
    --------------
        `path`: The file path or device path to the video stream.
        `backend`: The specific backend API to use for video capture (e.g., cv2.CAP_GSTREAMER, cv2.CAP_V4L2, etc.).

    Returns:
    --------------
        The video capture object if the path is valid and readable, otherwise None.
    """

    result: Optional[bool] = None
    cap: Optional[cv2.VideoCapture] = None

    try:
        logger.info("Trying camera %s", path)
        if backend is not None:
            cap = cv2.VideoCapture(path, backend)
        else:
            cap = cv2.VideoCapture(path)
        if pixel_format is not None:
            cap.set(
                cv2.CAP_PROP_FOURCC,
                cv2.VideoWriter.fourcc(*pixel_format),
            )
        if width is not None:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)

        if height is not None:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        if fps is not None:
            cap.set(cv2.CAP_PROP_FPS, float(fps))
        result, _ = cap.read()
        if not result:
            logger.debug("Camera failed %s", path)

    except Exception as err:
        logger.debug("Camera Error: %s", err)
        release_video_capture_safe(cap)

    if not result:
        release_video_capture_safe(cap)

    return cap if result else None


def release_video_capture_safe(cap: Optional[cv2.VideoCapture]) -> None:
    """
    Safely releases the camera capture.
    """
    try:
        if cap is not None:
            cap.release()
    except Exception as e:
        logger.error("Exception occurred while stopping camera capture: %s", e)
