from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Tuple

from app.adapters.avfoundation_capture_adapter import AVFoundationCaptureAdapter
from app.adapters.gstreamer_capture_adapter import GStreamerCaptureAdapter
from app.adapters.isolated_gstreamer_capture_adapter import (
    IsolatedGStreamerCaptureAdapter,
)
from app.adapters.picamera_capture_adapter import PicameraCaptureAdapter
from app.adapters.v4l2_capture_adapter import V4l2CaptureAdapter
from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.core.video_capture_abc import VideoCaptureABC
from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from app.schemas.camera import CameraSettings, DeviceType, DeviceStepwise
from app.schemas.photo import PhotoCameraSettings
from app.util.os_checks import is_macos, is_raspberry_pi

if TYPE_CHECKING:
    from app.services.camera.avfoundation_service import AVFoundationService
    from app.services.camera.gstreamer_service import GStreamerService
    from app.services.camera.picamera2_service import PicameraService
    from app.services.camera.v4l2_service import V4L2Service

_log = Logger(name=__name__)


class VideoDeviceAdapter:
    """
    A class responsible for managing video capturing devices.
    """

    def __init__(
        self,
        v4l2_service: "V4L2Service",
        gstreamer_service: "GStreamerService",
        picam_service: "PicameraService",
        avfoundation_service: "AVFoundationService",
    ) -> None:
        self.v4l2_service = v4l2_service
        self.gstreamer_service = gstreamer_service
        self.picam_service = picam_service
        self.avfoundation_service = avfoundation_service
        self.devices: List[DeviceType] = []

    def _try_device_props(
        self, device: str, camera_settings: CameraSettings
    ) -> Optional[Tuple[VideoCaptureABC, CameraSettings]]:
        api, device_path = GStreamerParser.parse_device_path(device)
        _log.info("Trying device: '%s', with device path: '%s'", device, device_path)
        if api is None:
            api = (
                "v4l2"
                if device_path.startswith("/dev/video")
                else (
                    "avfoundation"
                    if is_macos()
                    else "v4l2" if not is_raspberry_pi() else "picamera2"
                )
            )

        api_workers: Dict[str, Callable[[], VideoCaptureABC]] = {
            "avfoundation": lambda: AVFoundationCaptureAdapter(
                device,
                camera_settings=camera_settings,
                service=self.avfoundation_service,
            ),
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
            "libcamera": lambda: IsolatedGStreamerCaptureAdapter(
                device, camera_settings=camera_settings, service=self.gstreamer_service
            ),
        }

        cap_worker = api_workers.get(api)
        if not cap_worker:
            raise CameraNotFoundError("Video device is not available")

        cap = cap_worker()
        return cap, cap.settings

    def list_devices(self) -> List[DeviceType]:
        if is_macos():
            self.devices = self.avfoundation_service.list_video_devices()
            return self.devices

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
            return self.devices

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

        devices: List[DeviceType] = []

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
        _log.info("Setting up video device: %s", camera_settings.device)
        if camera_settings.device is not None:
            device_path = GStreamerParser.strip_api_prefix(camera_settings.device)
            video_device: Optional[str] = None
            for item in devices:
                if device_path in (item.device, item.path):
                    video_device = camera_settings.device
                    break

            if video_device is None:
                _log.error("Video device %s is not available", camera_settings.device)
                raise CameraNotFoundError("Video device is not available")
            else:
                _log.info(
                    "Found video device: %s, trying its settings",
                    video_device,
                )

                result = self._try_device_props(video_device, camera_settings)
                if result is None:
                    raise CameraDeviceError("Video capture failed")
                else:
                    return result
        else:
            result = None
            if len(devices) > 0:
                device_name = devices[0].device
                result = self._try_device_props(device_name, camera_settings)

            if result is None:
                raise CameraNotFoundError("Couldn't find video device")
            else:
                return result

    def setup_photo_capture(
        self, settings: PhotoCameraSettings
    ) -> Tuple[VideoCaptureABC, CameraSettings]:
        """Open a camera for still acquisition using its native still configuration."""
        api, device_path = GStreamerParser.parse_device_path(settings.device or "")
        if api == "picamera2":
            cap = PicameraCaptureAdapter(
                device_path, settings, self.picam_service, still=True
            )
            return cap, cap.settings
        return self.setup_video_capture(settings)

    def validate_photo_settings(self, settings: PhotoCameraSettings) -> None:
        """Reject unavailable devices and modes before interrupting a stream."""
        if settings.width is None or settings.height is None:
            raise CameraDeviceError("Photo presets require explicit dimensions.")
        devices = [
            item for item in self.list_devices() if item.device == settings.device
        ]
        if not devices:
            raise CameraNotFoundError("The photo preset camera is not available.")
        for item in devices:
            if settings.pixel_format and item.pixel_format != settings.pixel_format:
                continue
            if settings.media_type and item.media_type != settings.media_type:
                continue
            if isinstance(item, DeviceStepwise):
                dimensions_match = (
                    item.min_width <= settings.width <= item.max_width
                    and item.min_height <= settings.height <= item.max_height
                    and (settings.width - item.min_width) % max(1, item.width_step) == 0
                    and (settings.height - item.min_height) % max(1, item.height_step)
                    == 0
                )
                fps_matches = (
                    settings.fps is None or item.min_fps <= settings.fps <= item.max_fps
                )
            else:
                dimensions_match = (item.width, item.height) == (
                    settings.width,
                    settings.height,
                )
                fps_matches = (
                    settings.fps is None
                    or item.fps is None
                    or abs(item.fps - settings.fps) < 0.01
                )
            if dimensions_match and fps_matches:
                return
        raise CameraDeviceError(
            "The photo preset resolution, frame rate, or pixel format is not supported by this camera."
        )
