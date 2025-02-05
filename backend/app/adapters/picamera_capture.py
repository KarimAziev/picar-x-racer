from typing import TYPE_CHECKING, Tuple, cast

import numpy as np
from app.adapters.capture_adapter import VideoCaptureAdapter
from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.exceptions.camera import CameraDeviceError
from app.schemas.camera import CameraSettings
from cv2.typing import MatLike

if TYPE_CHECKING:
    from picamera2 import Picamera2

logger = Logger(name=__name__)


class PicameraCapture(VideoCaptureAdapter):
    def __init__(self, device: str, camera_settings: CameraSettings):
        from picamera2 import Picamera2

        device_id = GStreamerParser.strip_api_prefix(device)
        devices = Picamera2.global_camera_info()
        index = next((i for i, d in enumerate(devices) if d["Id"] == device_id), None)
        if index is None:
            raise CameraDeviceError("Video device is not found in picam2")

        self.picam2 = Picamera2(index)
        self._cap, self.settings = self._try_device_props(device, camera_settings)

    def _try_device_props(
        self, device: str, camera_settings: CameraSettings
    ) -> Tuple["Picamera2", CameraSettings]:
        """
        Configure the Picamera2 instance using the supplied camera settings.
        """
        fmt = "BGR888"

        if camera_settings.width is None or camera_settings.height is None:
            default_width, default_height = 1280, 720
            width = default_width
            height = default_height
        else:
            width = camera_settings.width
            height = camera_settings.height

        config = self.picam2.create_video_configuration(
            main={"size": (width, height), "format": fmt}
        )
        logger.info("Picamera2 config: %s", config)

        if camera_settings.fps is not None:
            micro = int((1 / camera_settings.fps) * 1_000_000)
            config["controls"]["FrameDurationLimits"] = (micro, micro)

        frame_limits = config.get("controls", {}).get("FrameDurationLimits")
        if frame_limits and frame_limits[0]:
            min_duration: int = frame_limits[0]
            fps = round(1_000_000 / min_duration)
            logger.info("Configured FPS: %.2f", fps)
        else:
            fps = None
            logger.warning("FrameDurationLimits not found in config")

            self.picam2.configure(config)

        try:
            self.picam2.start()
        except Exception as err:
            raise CameraDeviceError(f"Failed to start Picamera2: {err}")

        try:
            frame = self.picam2.capture_array()

        except Exception as err:
            self.picam2.stop()
            raise CameraDeviceError(f"Initial frame capture failed: {err}")

        if frame is None or not isinstance(frame, np.ndarray):
            self.picam2.stop()
            raise CameraDeviceError("Initial frame capture failed: No image data")

        frame = cast(np.ndarray, frame)
        configuration = self.picam2.camera_configuration()
        main_configuration = configuration["main"]

        logger.info(
            "configuration %s, main='%s'",
            configuration,
            main_configuration,
        )

        captured_height, captured_width = frame.shape[:2]
        updated_settings = {
            **camera_settings.model_dump(),
            "fps": fps,
            "device": device,
            "width": captured_width,
            "height": captured_height,
        }

        return self.picam2, CameraSettings(**updated_settings)

    def read(self) -> Tuple[bool, MatLike]:
        """
        Capture a single frame from the camera.
        Returns a tuple: (success, frame).
        In the Picamera2 case, we use capture_array() to get the frame.
        """
        try:
            frame = self.picam2.capture_array()
            if frame is not None:
                return True, cast(np.ndarray, frame)
            else:
                return False, np.empty((0, 0), dtype=np.uint8)
        except Exception as e:
            logger.error("Exception during Picamera2 frame capture: %s", e)
            return False, np.empty((0, 0), dtype=np.uint8)

    def release(self) -> None:
        """
        Stop the camera.
        """
        try:
            self.picam2.close()
        except Exception as e:
            logger.error("Exception occurred while stopping Picamera2: %s", e)
