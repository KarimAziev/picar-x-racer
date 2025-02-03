from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import cv2
from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from app.schemas.camera import CameraSettings, DeviceType
from app.util.device import try_video_path

logger = Logger(name=__name__)

if TYPE_CHECKING:
    from app.services.gstreamer_service import GStreamerService
    from app.services.v4l2_service import V4L2Service


class VideoDeviceAdapater(metaclass=SingletonMeta):
    """
    A singleton class responsible for managing video capturing devices.
    """

    def __init__(
        self, v4l2_manager: "V4L2Service", gstreamer_manager: "GStreamerService"
    ):
        self.v4l2_manager = v4l2_manager
        self.gstreamer_manager = gstreamer_manager
        self.devices: List[DeviceType] = []

    def try_device_props(
        self, device: str, camera_settings: CameraSettings
    ) -> Optional[Tuple[cv2.VideoCapture, CameraSettings]]:
        if camera_settings.use_gstreamer:
            pipeline = self.gstreamer_manager.setup_pipeline(
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
            device_path = GStreamerParser.strip_api_prefix(device)
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

            data = self.v4l2_manager.video_capture_format(device_path) or {}

            updated_settings = {
                **camera_settings.model_dump(),
                "device": device,
                "width": int(width),
                "height": int(height),
                "fps": float(fps),
                "pixel_format": data.get("pixel_format", camera_settings.pixel_format),
            }

        return cap, CameraSettings(**updated_settings)

    def list_devices(self) -> List[DeviceType]:
        v4l2_devices = self.v4l2_manager.list_video_devices()
        failed_devices = self.v4l2_manager.failed_devices
        gstreamer_devices = (
            self.gstreamer_manager.list_video_devices()
            if self.gstreamer_manager.gstreamer_available()
            else None
        )
        if gstreamer_devices is None:
            self.devices = v4l2_devices
            return v4l2_devices

        results: List[DeviceType] = []
        gstreamer_devices_paths = set()
        device_names: Dict[str, Optional[str]] = {}

        for item in gstreamer_devices:
            path = item.path
            if path:
                device_names[path] = item.name
            if not isinstance(path, str):
                continue
            if item.api != "v4l2":
                results.append(item)
                gstreamer_devices_paths.add(path)
            elif (
                path not in failed_devices
                and path not in self.v4l2_manager.succeed_devices
            ):
                results.append(item)

        devices = []

        for item in v4l2_devices:
            if item.device not in gstreamer_devices_paths:
                if not item.name:
                    item.name = device_names.get(item.device)
                devices.append(item)

        self.devices = devices + results

        return self.devices

    def setup_video_capture(
        self, camera_settings: CameraSettings
    ) -> Tuple[cv2.VideoCapture, CameraSettings]:
        devices = self.list_devices()
        if camera_settings.device is not None:
            device_path = GStreamerParser.strip_api_prefix(camera_settings.device)
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
