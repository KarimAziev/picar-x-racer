from typing import TYPE_CHECKING, Tuple

import cv2
from app.adapters.capture_adapter import VideoCaptureAdapter
from app.core.logger import Logger
from app.exceptions.camera import CameraDeviceError
from app.schemas.camera import CameraSettings
from app.util.device import release_video_capture_safe, try_video_path
from cv2.typing import MatLike

logger = Logger(name=__name__)

if TYPE_CHECKING:
    from app.services.gstreamer_service import GStreamerService


class GStreamerCapture(VideoCaptureAdapter):
    def __init__(
        self, device: str, camera_settings: CameraSettings, manager: "GStreamerService"
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
        pipeline = self.manager.setup_pipeline(
            device,
            width=camera_settings.width,
            height=camera_settings.height,
            fps=camera_settings.fps,
            pixel_format=camera_settings.pixel_format,
            media_type=camera_settings.media_type,
        )
        cap = try_video_path(pipeline, backend=cv2.CAP_GSTREAMER)
        if cap is None:
            raise CameraDeviceError("Video capture failed")
        updated_settings = {
            **camera_settings.model_dump(),
            "device": device,
        }

        return cap, CameraSettings(**updated_settings)
