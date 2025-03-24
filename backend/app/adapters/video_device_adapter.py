from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

from app.adapters.gstreamer_capture_adapter import GStreamerCaptureAdapter
from app.adapters.picamera_capture_adapter import PicameraCaptureAdapter
from app.adapters.v4l2_capture_adapter import V4l2CaptureAdapter
from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.core.video_capture_abc import VideoCaptureABC
from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from app.schemas.camera import CameraSettings, DeviceType
from app.util.os_checks import is_raspberry_pi

logger = Logger(name=__name__)

if TYPE_CHECKING:
    from app.services.camera.gstreamer_service import GStreamerService
    from app.services.camera.picamera2_service import PicameraService
    from app.services.camera.v4l2_service import V4L2Service


class VideoDeviceAdapter(metaclass=SingletonMeta):
    """
    A singleton class responsible for managing video capturing devices.
    """

    def __init__(
        self,
        v4l2_service: "V4L2Service",
        gstreamer_service: "GStreamerService",
        picam_service: "PicameraService",
    ):
        self.v4l2_service = v4l2_service
        self.gstreamer_service = gstreamer_service
        self.picam_service = picam_service
        self.devices: List[DeviceType] = []

    def try_device_props(
        self, device: str, camera_settings: CameraSettings
    ) -> Optional[Tuple[VideoCaptureABC, CameraSettings]]:
        api, device_path = GStreamerParser.parse_device_path(device)
        logger.info("device='%s', device_path='%s'", device, device_path)
        if api is None:
            api = (
                "v4l2"
                if device_path.startswith("/dev/video") or not is_raspberry_pi()
                else "picamera2"
            )

        api_workers: Dict[str, Callable[[], VideoCaptureABC]] = {
            "picamera2": lambda: PicameraCaptureAdapter(
                device_path, camera_settings=camera_settings, service=self.picam_service
            ),
            "v4l2": lambda: (
                V4l2CaptureAdapter(
                    device_path,
                    camera_settings=camera_settings,
                    service=self.v4l2_service,
                )
                if not camera_settings.use_gstreamer
                else GStreamerCaptureAdapter(
                    device,
                    camera_settings=camera_settings,
                    service=self.gstreamer_service,
                )
            ),
            "libcamera": lambda: GStreamerCaptureAdapter(
                device, camera_settings=camera_settings, service=self.gstreamer_service
            ),
        }

        cap_worker = api_workers.get(api)
        if not cap_worker:
            raise CameraNotFoundError("Video device is not available")

        cap = cap_worker()
        return cap, cap.settings

    def list_devices(self) -> List[DeviceType]:
        v4l2_devices = self.v4l2_service.list_video_devices()
        failed_devices = self.v4l2_service.failed_devices
        gstreamer_devices = (
            self.gstreamer_service.list_video_devices()
            if self.gstreamer_service.gstreamer_available()
            else None
        )
        picamera_devices = self.picam_service.list_video_devices()
        if gstreamer_devices is None:
            self.devices = v4l2_devices + picamera_devices
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
                and path not in self.v4l2_service.succeed_devices
            ):
                results.append(item)

        devices = []

        for item in v4l2_devices:
            if item.device not in gstreamer_devices_paths:
                if not item.name:
                    item.name = device_names.get(item.device)
                devices.append(item)

        self.devices = devices + results + picamera_devices

        return self.devices

    def setup_video_capture(
        self, camera_settings: CameraSettings
    ) -> Tuple[VideoCaptureABC, CameraSettings]:
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
