from typing import Dict, Optional, Tuple

from app.core.logger import Logger

logger = Logger(__name__)

from typing import Dict, Optional, Tuple


class GstreamerPipelineBuilder:
    pixel_format_props: Dict[str, Tuple[str, str]] = {
        # MJPEG -> Decode images
        "MJPG": ("image/jpeg", "v4l2jpegdec ! videoconvert"),
        "JPEG": ("image/jpeg", "v4l2jpegdec ! videoconvert"),  # Same as MJPG,
        "YUYV": ("video/x-raw, format=YUY2", "videoconvert"),  # YUYV -> Convert to BGR
        "RGB": ("video/x-raw, format=RGB", "videoconvert"),  # RGB directly
        "GRAY": ("video/x-raw, format=GRAY8", "videoconvert"),  # Grayscale -> Convert
        "YU12": ("video/x-raw, format=I420", "videoconvert"),  # YUV 4:2:0 -> Convert
        "H264": (
            "video/x-h264",
            "h264parse ! v4l2h264dec ! videoconvert",
        ),  # H.264 -> Parse and decode
        "YVYU": ("video/x-raw, format=YVYU", "videoconvert"),  # YUV variant -> Convert
        "VYUY": ("video/x-raw, format=VYUY", "videoconvert"),  # YUV variant -> Convert
        "UYVY": ("video/x-raw, format=UYVY", "videoconvert"),  # YUV variant -> Convert
        "NV12": ("video/x-raw, format=NV12", "videoconvert"),  # YUV 4:2:0 -> Convert
        "YV12": ("video/x-raw, format=YV12", "videoconvert"),  # YUV variant -> Convert
        "NV21": ("video/x-raw, format=NV21", "videoconvert"),  # NV21 variant -> Convert
        "RX24": ("video/x-raw, format=ABGR", "videoconvert"),  # 32-bit -> Convert
        "RGB3": ("video/x-raw, format=RGB", "videoconvert"),  # RGB3 -> Convert to BGR
        "BGR3": ("video/x-raw, format=BGR", "videoconvert"),  # BGR3 directly -> Convert
    }

    def __init__(self):
        self._device: Optional[str] = None
        self._width: Optional[int] = None
        self._height: Optional[int] = None
        self._fps: Optional[int] = None
        self._pixel_format: Optional[str] = None

    def device(self, device: str) -> "GstreamerPipelineBuilder":
        self._device = device
        return self

    def width(self, width: int) -> "GstreamerPipelineBuilder":
        self._width = width
        return self

    def height(self, height: int) -> "GstreamerPipelineBuilder":
        self._height = height
        return self

    def fps(self, fps: int) -> "GstreamerPipelineBuilder":
        self._fps = fps
        return self

    def pixel_format(self, pixel_format: str) -> "GstreamerPipelineBuilder":
        if pixel_format not in self.pixel_format_props:
            raise ValueError(
                f"Unsupported pixel format: {pixel_format}. "
                f"Supported formats: {list(self.pixel_format_props.keys())}"
            )
        self._pixel_format = pixel_format
        return self

    def build(self) -> str:
        if self._device is None:
            raise ValueError("Device is required")
        if self._width is None:
            raise ValueError("Width is required")
        if self._height is None:
            raise ValueError("Height is required")
        if self._fps is None:
            raise ValueError("FPS is required")
        if self._pixel_format is None:
            raise ValueError("Pixel format is required")

        source_format, decoder = self.pixel_format_props.get(
            self._pixel_format,
            (f"video/x-raw, format={self._pixel_format}", "videoconvert"),
        )

        pipeline = (
            f"libcamerasrc device={self._device} ! "
            f"{source_format}, width={self._width}, height={self._height}, framerate={self._fps}/1 ! "
            f"{decoder} ! video/x-raw, format=BGR ! "
            f"appsink"
        )

        return pipeline
