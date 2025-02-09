from typing import TYPE_CHECKING, Tuple, cast

import numpy as np
from app.core.logger import Logger
from app.core.video_capture_abc import VideoCaptureABC
from app.exceptions.camera import CameraDeviceError
from app.schemas.camera import CameraSettings
from cv2.typing import MatLike

logger = Logger(name=__name__)

if TYPE_CHECKING:
    from app.services.gstreamer_service import GStreamerService


class GStreamerCaptureAdapter(VideoCaptureABC):
    def __init__(
        self, device: str, camera_settings: CameraSettings, service: "GStreamerService"
    ) -> None:
        """
        Initializes the capture adapter by constructing a GStreamer pipeline
        based on the provided settings. The appsink element is configured to
        provide frames (as BGR images in a NumPy array). If the pipeline cannot be
        created or appsink is missing, a CameraDeviceError is raised.
        """
        super().__init__(service=service)
        try:
            import gi

            gi.require_version("Gst", "1.0")
            gi.require_version("GstApp", "1.0")
            from gi.repository import Gst  # type: ignore
        except ImportError:
            raise CameraDeviceError("GStreamer (gi) bindings are not available.")

        Gst.init(None)
        self.Gst = Gst

        pipeline_str = service.setup_pipeline(
            device,
            width=camera_settings.width,
            height=camera_settings.height,
            fps=camera_settings.fps,
            pixel_format=camera_settings.pixel_format,
            media_type=camera_settings.media_type,
        )

        if "appsink" in pipeline_str and "name=" not in pipeline_str:
            pipeline_str = pipeline_str.replace("appsink", "appsink name=appsink")

        logger.info("GStreamer pipeline: %s", pipeline_str)

        self.pipeline = cast(Gst.Pipeline, Gst.parse_launch(pipeline_str))

        self.appsink = self.pipeline.get_by_name("appsink")
        if self.appsink is None:
            raise CameraDeviceError("Pipeline did not contain an appsink element.")

        self.appsink.set_property("emit-signals", True)

        caps = Gst.Caps.from_string("video/x-raw, format=BGR")
        self.appsink.set_property("caps", caps)

        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            raise CameraDeviceError(
                "Unable to set the GStreamer pipeline to PLAYING state."
            )

        self._settings = CameraSettings(
            **{
                **camera_settings.model_dump(),
                "use_gstreamer": True,
                "device": device,
            }
        )

    def read(self) -> Tuple[bool, MatLike]:
        """
        Retrieves the next available frame from the GStreamer pipeline.
        Returns a tuple (status, frame) where status is True if a frame was
        successfully retrieved and frame is a NumPy array representing the image.
        """
        sample = self.appsink.emit("pull-sample") if self.appsink else None
        if not sample or not self.Gst:
            return (False, np.empty((0, 0), dtype=np.uint8))

        buffer = sample.get_buffer()
        caps = sample.get_caps()
        structure = caps.get_structure(0)
        try:
            width = structure.get_value("width")
            height = structure.get_value("height")
        except Exception as e:
            logger.error("Failed to read image dimensions from caps: %s", e)
            return (False, np.empty((0, 0), dtype=np.uint8))

        success, map_info = buffer.map(self.Gst.MapFlags.READ)
        if not success:
            return (False, np.empty((0, 0), dtype=np.uint8))
        try:
            frame = np.frombuffer(map_info.data, dtype=np.uint8)
            frame = frame.reshape((height, width, 3))
        except Exception as e:
            logger.error("Error converting buffer to NumPy array: %s", e)
            frame = None
            success = False
        finally:
            buffer.unmap(map_info)
        return (
            success,
            frame if frame is not None else np.empty((0, 0), dtype=np.uint8),
        )

    def release(self) -> None:
        """
        Stops the pipeline and releases its resources.
        """
        if self.pipeline and self.Gst is not None:
            self.pipeline.set_state(self.Gst.State.NULL)

    @property
    def settings(self) -> CameraSettings:
        """
        Returns the camera settings (including modifications like setting use_gstreamer=True).
        """
        return self._settings
