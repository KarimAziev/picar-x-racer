from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union, cast

import cv2
import numpy as np
from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.core.video_capture_abc import VideoCaptureABC
from app.exceptions.camera import CameraDeviceError
from app.schemas.camera import CameraSettings
from app.services.camera.picamera2_service import (
    PICAMERA2_TO_PIXEL_FORMATS_MAP,
    PIXEL_FORMATS_TO_PICAMERA2_MAP,
)

if TYPE_CHECKING:
    from app.services.camera.picamera2_service import PicameraService
    from cv2.typing import MatLike

    try:
        from picamera2 import Picamera2
    except Exception:
        pass

logger = Logger(name=__name__)


yuv_conversions: Dict[str, Union[int, None]] = {
    "YUV420": cv2.COLOR_YUV2BGR_I420,
    "YVU420": cv2.COLOR_YUV2BGR_I420,
    "NV12": cv2.COLOR_YUV2BGR_NV12,
    "NV21": cv2.COLOR_YUV2BGR_NV21,
    "YUYV": cv2.COLOR_YUV2BGR_YUY2,
    "YVYU": cv2.COLOR_YUV2BGR_YVYU,
}


rgb_conversions: Dict[str, Union[int, None]] = {
    "XBGR8888": cv2.COLOR_RGBA2BGR,
    "XRGB8888": None,  # Already BGR order.
    "BGR888": cv2.COLOR_RGB2BGR,
    "RGB888": None,  # Already in BGR order.
    "BGR161616": None,  # Already in BGR order.
}

color_conversions: Dict[str, Union[int, None]] = {
    **yuv_conversions,
    **rgb_conversions,
}


class PicameraCaptureAdapter(VideoCaptureABC):
    def __init__(
        self, device: str, camera_settings: CameraSettings, service: "PicameraService"
    ):
        super().__init__(service=service)

        import picamera2.formats as formats
        from picamera2 import Picamera2

        self.service = service

        device_id = GStreamerParser.strip_api_prefix(device)
        devices = Picamera2.global_camera_info()
        index = next((i for i, d in enumerate(devices) if d["Id"] == device_id), None)
        if index is None:
            raise CameraDeviceError("Video device is not found in picam2")

        self.picam2 = Picamera2(index)
        self.formats = formats
        self.format: Optional[str] = None
        self._cap, self._settings = self._try_device_props(device, camera_settings)

    @property
    def settings(self) -> CameraSettings:
        """Concrete implementation of the abstract settings property."""
        return self._settings

    @staticmethod
    def fps_to_frame_interval(fps: float) -> int:
        """Convert frames per second (fps) to a frame interval in microseconds."""
        return int(1_000_000 / fps)

    @staticmethod
    def frame_interval_to_fps(interval: float) -> float:
        """Convert a frame interval in microseconds to frames per second (fps)."""
        return 1_000_000 / interval

    def _try_device_props(
        self, device: str, camera_settings: CameraSettings
    ) -> Tuple["Picamera2", CameraSettings]:
        """
        Configure the Picamera2 instance using the supplied camera settings.
        """

        pixel_format = camera_settings.pixel_format
        fmt = None

        if camera_settings.width is None or camera_settings.height is None:
            default_width, default_height = 1280, 720
            width = default_width
            height = default_height
        else:
            width = camera_settings.width
            height = camera_settings.height

        main_config: Dict[str, Any] = {"size": (width, height)}

        if pixel_format:
            if (
                not self.formats.is_YUV(pixel_format)
                and not self.formats.is_RGB(pixel_format)
                and pixel_format != "MJPEG"
            ):
                fmt = PIXEL_FORMATS_TO_PICAMERA2_MAP.get(pixel_format)
            else:
                fmt = pixel_format

        if fmt is None:
            pixel_format = None

        if fmt:
            main_config["format"] = fmt

        fps_interval = (
            self.fps_to_frame_interval(camera_settings.fps)
            if camera_settings.fps is not None
            else None
        )

        logger.info("fps='%s', fps_interval=%s", camera_settings.fps, fps_interval)

        config = (
            self.picam2.create_video_configuration(main=main_config)
            if fps_interval is None
            else self.picam2.create_video_configuration(
                main=main_config,
                controls={"FrameDurationLimits": (fps_interval, fps_interval)},
            )
        )
        self.format = config.get("main", {}).get("format")

        self.picam2.align_configuration(config)

        self.picam2.configure(config)
        logger.info("Picamera2 config: %s", config)

        frame_limits = config.get("controls", {}).get("FrameDurationLimits")
        logger.info("frame_limits=%s", frame_limits)
        if frame_limits and frame_limits[0]:
            min_duration: int = frame_limits[0]
            fps = round(self.frame_interval_to_fps(min_duration))
            logger.info("Configured FPS: %.2f", fps)
        else:
            fps = None
            logger.warning("FrameDurationLimits not found in config")

        try:
            self.picam2.start()
        except Exception as err:
            self.release()
            raise CameraDeviceError(f"Failed to start Picamera2: {err}")

        try:
            frame = self.picam2.capture_array()
        except Exception as err:
            self.release()
            raise CameraDeviceError(f"Initial frame capture failed: {err}")

        if frame is None or not isinstance(frame, np.ndarray):
            self.release()
            raise CameraDeviceError("Initial frame capture failed: No image data")

        frame = cast(np.ndarray, frame)

        pixel_format = (
            PICAMERA2_TO_PIXEL_FORMATS_MAP.get(self.format)
            if self.format and self.format != "MJPEG"
            else self.format
        )

        updated_settings = {
            **camera_settings.model_dump(),
            "fps": fps,
            "use_gstreamer": False,
            "pixel_format": pixel_format,
            "device": f"{'picamera2'}:{device}",
            "width": width,
            "height": height,
        }

        return self.picam2, CameraSettings(**updated_settings)

    def read(self) -> Tuple[bool, "MatLike"]:
        """
        Capture a single frame from the camera.
        Returns a tuple: (success, frame).
        In the Picamera2 case, we use capture_array() to get the frame.
        """
        try:

            frame = self.picam2.capture_array()

            if frame is not None:
                frame = cast(np.ndarray, frame)
                if self.format:
                    convert_color = color_conversions.get(self.format)

                    frame = (
                        cv2.cvtColor(frame, convert_color) if convert_color else frame
                    )
                return True, frame
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
            self.picam2.stop()
            logger.info("Picamera stopped")
            self.picam2.close()
            logger.info("Picamera closed")
        except Exception as e:
            logger.error("Exception occurred while stopping Picamera2: %s", e)
