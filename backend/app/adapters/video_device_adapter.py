from typing import List, Optional, Tuple

import cv2
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
        Initializes the VideoDeviceAdapater instance. Sets up the logger,
        and initializes attributes for tracking video devices and failed attempts.
        """
        self.logger = Logger(name=__name__)
        self.video_device: Optional[CameraInfo] = None
        self.video_devices: List[CameraInfo] = []

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
            )
            cap = try_video_path(pipeline, backend=cv2.CAP_GSTREAMER)
            if cap is None:
                return None
            updated_settings = {
                **camera_settings.model_dump(),
                "device": device,
            }
        else:
            cap = try_video_path(
                device,
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

            data = V4L2.video_capture_format(device) or {}

            updated_settings = {
                **camera_settings.model_dump(),
                "device": device,
                "width": int(width),
                "height": int(height),
                "fps": int(fps),
                "pixel_format": data.get("pixel_format", camera_settings.pixel_format),
            }

        return cap, CameraSettings(**updated_settings)

    def setup_video_capture(
        self, camera_settings: CameraSettings
    ) -> Tuple[cv2.VideoCapture, CameraSettings]:
        if camera_settings.device is not None:
            self.video_devices = V4L2.list_camera_devices()
            self.video_device = V4L2.find_device_info(camera_settings.device)
            if self.video_device is None:
                raise CameraNotFoundError("Video device is not available")
            else:
                (device_path, _) = self.video_device
                result = self.try_device_props(device_path, camera_settings)
                if result is None:
                    raise CameraDeviceError("Video capture failed")
                else:
                    return result
        else:
            self.video_devices = V4L2.list_camera_devices()
            result = None
            if len(self.video_devices) > 0:
                device, _ = self.video_devices[0]
                result = self.try_device_props(device, camera_settings)

            if result is None:
                raise CameraNotFoundError("Couldn't find video device")
            else:
                return result
