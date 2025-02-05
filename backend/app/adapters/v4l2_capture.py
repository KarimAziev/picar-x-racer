from typing import TYPE_CHECKING, Tuple

import cv2
from app.adapters.capture_adapter import VideoCaptureAdapter
from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.exceptions.camera import CameraDeviceError
from app.schemas.camera import CameraSettings
from app.util.device import release_video_capture_safe
from cv2.typing import MatLike

logger = Logger(name=__name__)

if TYPE_CHECKING:
    from app.services.v4l2_service import V4L2Service


class V4l2Capture(VideoCaptureAdapter):

    def __init__(
        self, device: str, camera_settings: CameraSettings, manager: "V4L2Service"
    ):
        self.manager = manager
        self._cap, self.settings = self._try_device_props(device, camera_settings)

    def read(self) -> Tuple[bool, MatLike]:
        return self._cap.read()

    def release(self) -> None:
        release_video_capture_safe(self._cap)

    def _try_device_props(
        self, device: str, camera_settings: CameraSettings
    ) -> Tuple[cv2.VideoCapture, CameraSettings]:
        device_path = GStreamerParser.strip_api_prefix(device)
        cap = cv2.VideoCapture(device_path, cv2.CAP_V4L2)
        if camera_settings.pixel_format is not None:
            cap.set(
                cv2.CAP_PROP_FOURCC,
                cv2.VideoWriter.fourcc(*camera_settings.pixel_format),
            )
        if camera_settings.width is not None:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_settings.width)

        if camera_settings.height is not None:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_settings.height)

        if camera_settings.fps is not None:
            cap.set(cv2.CAP_PROP_FPS, float(camera_settings.fps))
        result, _ = cap.read()

        if not result:
            release_video_capture_safe(cap)
            raise CameraDeviceError("Video capture failed")

        width, height, fps = (
            cap.get(x)
            for x in (
                cv2.CAP_PROP_FRAME_WIDTH,
                cv2.CAP_PROP_FRAME_HEIGHT,
                cv2.CAP_PROP_FPS,
            )
        )

        data = self.manager.video_capture_format(device_path) or {}

        updated_settings = {
            **camera_settings.model_dump(),
            "device": device,
            "width": int(width),
            "height": int(height),
            "fps": float(fps),
            "pixel_format": data.get("pixel_format", camera_settings.pixel_format),
        }
        return cap, CameraSettings(**updated_settings)
