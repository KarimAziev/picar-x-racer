from typing import List, Optional, Tuple

import cv2
from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from app.managers.gstreamer_manager import GstreamerManager
from app.managers.v4l2_manager import V4L2, CameraInfo
from app.schemas.camera import CameraSettings
from app.util.device import try_video_path


class VideoDeviceAdapater(metaclass=SingletonMeta):
    """
    A singleton class responsible for managing video capturing devices.
    """

    def __init__(self):
        """
        Initializes the VideoDeviceAdapater instance.
        """
        self.logger = Logger(name=__name__)
        self.video_devices: List[CameraInfo] = []

    @staticmethod
    def find_device_info(device: str) -> Optional[str]:
        """
        Finds the device info of a specific camera device from the list of available camera devices.

        Searches for the given device in the list of available camera devices and
        returns its associated information (e.g., device path and category).

        Args:
            device: The path to the camera device (e.g., `/dev/video0`).

        Returns:
            The device path.
        """
        devices = (
            V4L2.list_camera_device_names()
            + GstreamerManager.list_camera_device_names()
        )
        for device_path in devices:
            if device_path == device:
                return device_path

    @staticmethod
    def try_device_props(
        device: str, camera_settings: CameraSettings
    ) -> Optional[Tuple[cv2.VideoCapture, CameraSettings]]:
        if camera_settings.use_gstreamer:
            pipeline = GstreamerManager.setup_pipeline(
                device,
                width=camera_settings.width,
                height=camera_settings.height,
                fps=camera_settings.fps,
                pixel_format=camera_settings.pixel_format,
                media_type=camera_settings.media_type,
            )
            cap = try_video_path(pipeline, backend=cv2.CAP_GSTREAMER)
            if cap is None:
                return None
            updated_settings = {
                **camera_settings.model_dump(),
                "device": device,
            }
        else:
            _, device_path = GStreamerParser.parse_device_path(device)
            cap = try_video_path(
                device_path,
                backend=cv2.CAP_V4L2,
                width=camera_settings.width,
                height=camera_settings.height,
                fps=camera_settings.fps,
                pixel_format=camera_settings.pixel_format,
            )
            if cap is None:
                return None
            width, height, fps = (
                cap.get(x)
                for x in (
                    cv2.CAP_PROP_FRAME_WIDTH,
                    cv2.CAP_PROP_FRAME_HEIGHT,
                    cv2.CAP_PROP_FPS,
                )
            )

            data = V4L2.video_capture_format(device_path) or {}

            updated_settings = {
                **camera_settings.model_dump(),
                "device": device,
                "width": int(width),
                "height": int(height),
                "fps": int(fps),
                "pixel_format": data.get("pixel_format", camera_settings.pixel_format),
            }

        return cap, CameraSettings(**updated_settings)

    @staticmethod
    def list_devices():
        if GstreamerManager.gstreamer_available():
            return (
                GstreamerManager.list_video_devices_with_formats()
                + V4L2.list_video_devices_with_formats()
            )
        else:
            return V4L2.list_video_devices_with_formats()

    def setup_video_capture(
        self, camera_settings: CameraSettings
    ) -> Tuple[cv2.VideoCapture, CameraSettings]:
        if camera_settings.device is not None:
            video_device = self.find_device_info(camera_settings.device)
            if video_device is None:
                raise CameraNotFoundError("Video device is not available")
            else:
                device_path = video_device
                result = self.try_device_props(device_path, camera_settings)
                if result is None:
                    raise CameraDeviceError("Video capture failed")
                else:
                    return result
        else:
            devices = (
                V4L2.list_camera_device_names()
                + GstreamerManager.list_camera_device_names()
            )
            result = None
            if len(devices) > 0:
                result = self.try_device_props(devices[0], camera_settings)

            if result is None:
                raise CameraNotFoundError("Couldn't find video device")
            else:
                return result
