import shutil
from functools import lru_cache
from typing import Optional, Tuple

import cv2
from app.core.logger import Logger
from app.exceptions.camera import CameraInfoNotFound
from app.managers.v4l2_manager import V4L2
from app.util.gstreamer_pipeline_builder import GstreamerPipelineBuilder

logger = Logger(__name__)


class GstreamerManager:
    @staticmethod
    @lru_cache()
    def check_gstreamer() -> Tuple[bool, bool]:
        """
        Checks the availability of GStreamer in OpenCV and on the system.

        Returns:
        --------------
            A tuple with two boolean values:
            - Whether GStreamer is supported in OpenCV.
            - Whether GStreamer is installed on the system by looking for the `gst-launch-1.0`.

        Example:
        --------------
        ```python
        gstreamer_cv2, gstreamer_system = GstreamerManager.check_gstreamer()
        print(f"GStreamer in OpenCV: {gstreamer_cv2}")
        print(f"GStreamer on system: {gstreamer_system}")
        ```
        """
        gstreamer_in_cv2 = False
        try:
            build_info = cv2.getBuildInformation()
            if "GStreamer" in build_info and "YES" in build_info:
                gstreamer_in_cv2 = True
        except Exception as e:
            logger.error("Error while checking OpenCV build information: %s", e)

        gstreamer_on_system = False
        try:
            if shutil.which("gst-launch-1.0") is not None:
                gstreamer_on_system = True
        except Exception as e:
            logger.error("Error while checking system for GStreamer: %s", e)

        return gstreamer_in_cv2, gstreamer_on_system

    @staticmethod
    def gstreamer_available():
        gstreamer_cv2, gstreamer_system = GstreamerManager.check_gstreamer()
        return gstreamer_cv2 and gstreamer_system

    @staticmethod
    def setup_pipeline(
        device: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        pixel_format: Optional[str] = None,
    ) -> str:

        if width is None or height is None or fps is None or pixel_format is None:
            default_props = V4L2.video_capture_format(device)
            if default_props is None:
                raise CameraInfoNotFound(f"Device info for {device} is not found")

            width = width or default_props.get("width")
            height = height or default_props.get("height")
            pixel_format = pixel_format or default_props.get("pixel_format")

        fps = int(fps or 30)

        return (
            GstreamerPipelineBuilder()
            .device(device)
            .fps(fps)
            .height(height)
            .width(width)
            .pixel_format(pixel_format)
            .build()
        )
