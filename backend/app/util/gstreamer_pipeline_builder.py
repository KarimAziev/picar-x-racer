from functools import lru_cache
from typing import Callable, Dict, List, Optional, Tuple, Union

from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.exceptions.camera import CameraDeviceError

logger = Logger(__name__)

try:
    import gi

    gi.require_version("Gst", "1.0")
    from gi.repository import Gst  # type: ignore

    Gst.init(None)
except ImportError:
    Gst = None

StringOrNoneFunction = Callable[[], Optional[str]]

_PIXEL_FORMAT_PROPS: Dict[str, Tuple[str, Optional[str]]] = {
    "YUYV": ("video/x-raw, format=YUY2", "videoconvert"),  # YUYV -> Convert to BGR
    "RGB": ("video/x-raw, format=RGB", "videoconvert"),  # RGB directly
    "GRAY": ("video/x-raw, format=GRAY8", "videoconvert"),  # Grayscale -> Convert
    "GREY": ("video/x-raw, format=GRAY8", "videoconvert"),  # Grayscale -> Convert
    "YU12": ("video/x-raw, format=I420", "videoconvert"),  # YUV 4:2:0 -> Convert
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


class GstreamerPipelineBuilder:
    device_api_prop = {
        "libcamerasrc": "camera-name",
        "v4l2src": "device",
    }

    def __init__(self):
        self._device: Optional[str] = None
        self._width: Optional[int] = None
        self._height: Optional[int] = None
        self._fps: Optional[int] = None
        self._pixel_format: Optional[str] = None
        self._media_type: Optional[str] = None
        self._api: Optional[str] = None
        self.decoders: Dict[
            str, Union[None, str, List[Union[str, StringOrNoneFunction]]]
        ] = {
            "image/jpeg": [GstreamerPipelineBuilder.jpegdecoder, "videoconvert"],
            "video/x-h264": [
                GstreamerPipelineBuilder.h264parser,
                GstreamerPipelineBuilder.h264decoder,
            ],
        }

        self.pixel_format_props: Dict[
            str,
            Tuple[str, Union[None, str, List[Union[str, StringOrNoneFunction]]]],
        ] = {
            **_PIXEL_FORMAT_PROPS,
            "MJPG": (
                "image/jpeg",
                [GstreamerPipelineBuilder.jpegdecoder, "videoconvert"],
            ),
            "JPEG": (
                "image/jpeg",
                [GstreamerPipelineBuilder.jpegdecoder, "videoconvert"],
            ),
            "H264": (
                "video/x-h264",
                [
                    GstreamerPipelineBuilder.h264parser,
                    GstreamerPipelineBuilder.h264decoder,
                ],
            ),
        }

    def _mapconcat_decoders(
        self, decoders: List[Union[str, StringOrNoneFunction]]
    ) -> str:
        decoders_pipeline: List[str] = []

        for decoder in decoders:
            if callable(decoder):
                decoder = decoder()
                if decoder is None:
                    raise CameraDeviceError("Failed to find decoder")
                decoders_pipeline.append(decoder)
            else:
                decoders_pipeline.append(decoder)
        return " ! ".join(decoders_pipeline)

    @staticmethod
    def find_alternative(plugins: List[str]) -> Optional[str]:
        if Gst is None:
            return None
        for plugin_name in plugins:
            if GstreamerPipelineBuilder.plugin_available(plugin_name):
                return plugin_name

    @staticmethod
    @lru_cache(maxsize=None)
    def plugin_available(plugin) -> Optional[str]:
        if Gst is None:
            return None
        return plugin if Gst.ElementFactory.find(plugin) else None

    @staticmethod
    @lru_cache()
    def h264decoder():
        return GstreamerPipelineBuilder.find_alternative(
            ["v4l2h264dec", "omxh264dec", "nvh264dec", "avdec_h264"]
        )

    @staticmethod
    @lru_cache()
    def h264parser():
        return GstreamerPipelineBuilder.find_alternative(["v4l2h264parse", "h264parse"])

    @staticmethod
    @lru_cache()
    def jpegdecoder():
        return GstreamerPipelineBuilder.find_alternative(
            ["v4l2jpegdec", "jpegdec", "avdec_mjpeg"]
        )

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

        decoder = self.decoders.get(self._media_type) if self._media_type else None

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

        if decoder and isinstance(decoder, list):
            try:
                decoder = self._mapconcat_decoders(decoder)
            except CameraDeviceError:
                raise CameraDeviceError(
                    f"Failed to find decoder for '{self._pixel_format or source_media_format}'"
                )

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
                "appsink name=appsink",
            ]
            if item
        )

        return pipeline
