from typing import TYPE_CHECKING, List, Optional, Set, Tuple, Union

import cv2
from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from app.managers.gstreamer_manager import GstreamerManager
from app.schemas.camera import CameraSettings, DeviceStepwise, DiscreteDevice
from app.util.device import try_video_path

logger = Logger(name=__name__)

if TYPE_CHECKING:
    from app.services.v4l2_service import V4L2Service


class VideoDeviceAdapater(metaclass=SingletonMeta):
    def __init__(self, v4l2: "V4L2Service"):
        self.v4l2 = v4l2
        self.devices: List[Union[DeviceStepwise, DiscreteDevice]] = []

    """
    A singleton class responsible for managing video capturing devices.
    """

    def find_device_info(self, device: str) -> Optional[str]:
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
            self.v4l2.list_camera_device_names()
            + GstreamerManager.list_camera_device_names()
        )
        _, device_path = GStreamerParser.parse_device_path(device)
        for device_str in devices:
            _, known_device_path = GStreamerParser.parse_device_path(device_str)
            if known_device_path == device_path:
                return device_path

    def list_device_names(self):
        v4l2_devices = self.v4l2.list_camera_device_names()
        failed_devices = self.v4l2.failed_devices
        gstreamer_devices = GstreamerManager.list_camera_device_names()
        devices: Set[str] = set()

        for device_str in gstreamer_devices:
            if device_str not in failed_devices and device_str not in v4l2_devices:
                devices.add(device_str)

        return list(devices) + v4l2_devices

    def try_device_props(
        self, device: str, camera_settings: CameraSettings
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

            data = self.v4l2.video_capture_format(device_path) or {}

            updated_settings = {
                **camera_settings.model_dump(),
                "device": device,
                "width": int(width),
                "height": int(height),
                "fps": int(fps),
                "pixel_format": data.get("pixel_format", camera_settings.pixel_format),
            }

        return cap, CameraSettings(**updated_settings)

    def list_devices(self) -> List[
        Union[
            DeviceStepwise,
            DiscreteDevice,
        ]
    ]:

        v4l2_devices = self.v4l2.list_video_devices_ext()
        failed_devices = self.v4l2.failed_devices
        gstreamer_devices = (
            GstreamerManager.list_video_devices_with_formats()
            if GstreamerManager.gstreamer_available()
            else None
        )
        if gstreamer_devices is None:
            self.devices = v4l2_devices
            return v4l2_devices

        results: List[
            Union[
                DeviceStepwise,
                DiscreteDevice,
            ]
        ] = []
        gstreamer_devices_paths = set()

        for item in gstreamer_devices:
            path = item.path
            if not isinstance(path, str):
                continue
            if item.api != "v4l2":
                results.append(item)
                gstreamer_devices_paths.add(path)
            elif path not in failed_devices and path not in self.v4l2.succeed_devices:
                results.append(item)

        self.devices = [
            item
            for item in v4l2_devices
            if item.device not in gstreamer_devices_paths
            and f"{item.device}:{item.pixel_format}"
        ] + results

        return self.devices

    def setup_video_capture(
        self, camera_settings: CameraSettings
    ) -> Tuple[cv2.VideoCapture, CameraSettings]:
        devices = self.list_devices()
        if camera_settings.device is not None:
            _, device_path = GStreamerParser.parse_device_path(camera_settings.device)
            video_device: Optional[str] = None
            for item in devices:
                if device_path in (item.device, item.path):
                    video_device = camera_settings.device
                    break

            if video_device is None:
                raise CameraNotFoundError("Video device is not available")
            else:
                result = self.try_device_props(video_device, camera_settings)
                if result is None:
                    raise CameraDeviceError("Video capture failed")
                else:
                    return result
        else:
            result = None
            if len(devices) > 0:
                device_name = devices[0].device
                result = self.try_device_props(device_name, camera_settings)

            if result is None:
                raise CameraNotFoundError("Couldn't find video device")
            else:
                return result
