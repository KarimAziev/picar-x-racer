from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from app.adapters.capture_adapter import VideoCaptureAdapter
from app.adapters.gstreamer_capture import GStreamerCapture
from app.adapters.picamera_capture import PicameraCapture
from app.adapters.v4l2_capture import V4l2Capture
from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from app.schemas.camera import CameraSettings, DeviceType

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
    ) -> Optional[Tuple[VideoCaptureAdapter, CameraSettings]]:
        api, device_path = GStreamerParser.parse_device_path(device)
        logger.info("device='%s', device_path='%s'", device, device_path)

        cap = (
            GStreamerCapture(
                device, camera_settings=camera_settings, manager=self.gstreamer_manager
            )
            if camera_settings.use_gstreamer
            else (
                V4l2Capture(
                    device, camera_settings=camera_settings, manager=self.v4l2_manager
                )
                if api == "v4l2" or device_path.startswith("/dev/video")
                else PicameraCapture(device, camera_settings=camera_settings)
            )
        )
        return cap, cap.settings

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
    ) -> Tuple[VideoCaptureAdapter, CameraSettings]:
        devices = self.list_devices()
        logger.info("setup_video_capture device=%s", camera_settings.device)
        if camera_settings.device is not None:
            device_path = GStreamerParser.strip_api_prefix(camera_settings.device)
            video_device: Optional[str] = None
            for item in devices:
                if device_path in (item.device, item.path):
                    video_device = camera_settings.device
                    break

            logger.info(
                "video_device found=%s, camera_settings.device='%s'",
                video_device,
                camera_settings.device,
            )

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
