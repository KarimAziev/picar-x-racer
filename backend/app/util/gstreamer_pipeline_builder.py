from typing import Dict, Optional, Tuple

from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger

logger = Logger(__name__)


class GstreamerPipelineBuilder:
    decoders: Dict[str, str] = {
        "image/jpeg": "jpegdec ! video/x-raw ! videoconvert",
        "video/x-h264": "h264parse ! v4l2h264dec",
    }
    device_api_prop = {
        "libcamerasrc": "camera-name",
        "v4l2src": "device",
    }
    pixel_format_props: Dict[str, Tuple[str, Optional[str]]] = {
        # MJPEG -> Decode images
        "MJPG": ("image/jpeg", "jpegdec ! videoconvert"),
        "JPEG": ("image/jpeg", "v4l2jpegdec ! videoconvert"),
        "YUYV": ("video/x-raw, format=YUY2", "videoconvert"),  # YUYV -> Convert to BGR
        "RGB": ("video/x-raw, format=RGB", "videoconvert"),  # RGB directly
        "GRAY": ("video/x-raw, format=GRAY8", "videoconvert"),  # Grayscale -> Convert
        "GREY": ("video/x-raw, format=GRAY8", "videoconvert"),  # Grayscale -> Convert
        "YU12": ("video/x-raw, format=I420", "videoconvert"),  # YUV 4:2:0 -> Convert
        "H264": (
            "video/x-h264",
            "h264parse ! v4l2h264dec",
        ),  # H.264 -> Parse and decode
        "YVYU": ("video/x-raw, format=YVYU", "videoconvert"),  # YUV variant -> Convert
        "VYUY": ("video/x-raw, format=VYUY", "videoconvert"),  # YUV variant -> Convert
        "UYVY": ("video/x-raw, format=UYVY", "videoconvert"),  # YUV variant -> Convert
        "NV12": (
            "video/x-raw, format=NV12",
            "videoconvert",
        ),  # YUV 4:2:0 -> Convert
        "YV12": ("video/x-raw, format=YV12", "videoconvert"),  # YUV variant -> Convert
        "NV21": ("video/x-raw, format=NV21", "videoconvert"),  # NV21 variant -> Convert
        "RX24": ("video/x-raw, format=ABGR", "videoconvert"),  # 32-bit -> Convert
        "RGB3": ("video/x-raw, format=RGB", "videoconvert"),  # RGB3 -> Convert to BGR
        "BGR3": ("video/x-raw, format=BGR", ""),  # BGR3 directly -> Convert
    }

    def __init__(self):
        self._device: Optional[str] = None
        self._width: Optional[int] = None
        self._height: Optional[int] = None
        self._fps: Optional[int] = None
        self._pixel_format: Optional[str] = None
        self._media_type: Optional[str] = None
        self._api: Optional[str] = None

    def device(self, device: str) -> "GstreamerPipelineBuilder":
        api, device_path = GStreamerParser.parse_device_path(device)

        self._device = device_path
        self._api = f"{api}src" if api and not api.endswith("src") else api

        return self

    def width(self, width: Optional[int]) -> "GstreamerPipelineBuilder":
        self._width = width
        return self

    def height(self, height: Optional[int]) -> "GstreamerPipelineBuilder":
        self._height = height
        return self

    def fps(self, fps: Optional[int]) -> "GstreamerPipelineBuilder":
        self._fps = fps
        return self

    def pixel_format(self, pixel_format: Optional[str]) -> "GstreamerPipelineBuilder":
        self._pixel_format = pixel_format
        return self

    def media_type(self, media_type: Optional[str]) -> "GstreamerPipelineBuilder":
        self._media_type = media_type
        return self

    def build(self) -> str:
        api = self._api or "v4l2src"
        device_prop_name = self.device_api_prop.get(api, "device")

        source = f"{api} {device_prop_name}={self._device}" if self._device else api

        source_media_format = (
            ", ".join(
                [
                    item
                    for item in [
                        self._media_type,
                        f"format={self._pixel_format}" if self._pixel_format else None,
                    ]
                    if item
                ]
            )
            if self._media_type
            else None
        )

        decoder: Optional[str] = (
            self.decoders.get(self._media_type) if self._media_type else None
        )

        if source_media_format is None:
            source_format, source_decoder = (
                self.pixel_format_props.get(
                    self._pixel_format,
                    (f"video/x-raw, format={self._pixel_format}", "videoconvert"),
                )
                if self._pixel_format
                else ("video/x-raw", "videoconvert")
            )
            source_media_format = source_format
            decoder = source_decoder

        source_format_data = ",".join(
            [
                item
                for item in [
                    source_media_format,
                    f"width={self._width}" if self._width is not None else None,
                    f"height={self._height}" if self._height is not None else None,
                    f"framerate={self._fps}/1" if self._fps is not None else None,
                ]
                if item
            ]
        )

        pipeline = " ! ".join(
            item
            for item in [
                source,
                source_format_data,
                decoder if isinstance(decoder, str) else "videoconvert",
                "appsink",
            ]
            if item
        )

        return pipeline
