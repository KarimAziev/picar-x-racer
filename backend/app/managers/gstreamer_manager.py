import shutil
import subprocess
from functools import lru_cache
from typing import List, Optional, Set, Tuple, Union

import cv2
from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.schemas.camera import DeviceStepwise, DiscreteDevice
from app.util.gstreamer_pipeline_builder import GstreamerPipelineBuilder

logger = Logger(__name__)


class GstreamerManager:
    @staticmethod
    @lru_cache()
    def list_video_devices_with_formats() -> (
        List[Union[DeviceStepwise, DiscreteDevice]]
    ):
        """
        Lists video capture devices using gst-device-monitor-1.0.
        """
        lines: Optional[str] = None
        try:
            result = subprocess.run(
                ["gst-device-monitor-1.0", "Video"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            lines = result.stdout.strip()

        except FileNotFoundError as e:
            return []
        except subprocess.CalledProcessError as e:
            logger.error("Failed to run 'gst-device-monitor-1.0':", e)

        except Exception:
            logger.error("Unexpected exception occurred: ", exc_info=True)

        return GStreamerParser().parse(lines) if lines else []

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
        media_type: Optional[str] = None,
    ) -> str:

        if width is None or height is None or fps is None or pixel_format is None:

            width = width
            height = height
            pixel_format = pixel_format

        fps = int(fps) if fps else None

        return (
            GstreamerPipelineBuilder()
            .device(device)
            .media_type(media_type)
            .fps(fps)
            .height(height)
            .width(width)
            .pixel_format(pixel_format)
            .build()
        )
