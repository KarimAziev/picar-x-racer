"""
gstreamer_service.py – a service using Gst.DeviceMonitor and native getters
to yield a list of DeviceType objects.
"""

import shutil
from functools import lru_cache
from typing import List, Optional, Tuple

from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.schemas.camera import DeviceStepwise, DeviceType, DiscreteDevice
from app.util.gstreamer_pipeline_builder import GstreamerPipelineBuilder
from app.util.video_checksum import get_dev_video_checksum

logger = Logger(__name__)


class GStreamerService(metaclass=SingletonMeta):
    @staticmethod
    @lru_cache()
    def check_gstreamer() -> Tuple[bool, bool]:
        """
        Checks the availability of GStreamer in OpenCV and on the system.

        Returns:
        --------------
            A tuple with two boolean values:
            - Whether GStreamer is supported in OpenCV.
            - Whether GStreamer is installed on the system by looking for the `gst-launch-1.0`.

        Example:
        --------------
        ```python
        gstreamer_cv2, gstreamer_system = GStreamerService.check_gstreamer()
        print(f"GStreamer in OpenCV: {gstreamer_cv2}")
        print(f"GStreamer on system: {gstreamer_system}")
        ```
        """
        import cv2

        gstreamer_in_cv2 = False
        try:
            build_info = cv2.getBuildInformation()
            if "GStreamer" in build_info and "YES" in build_info:
                gstreamer_in_cv2 = True
        except Exception as e:
            logger.error("Error while checking OpenCV build information: %s", e)

        gstreamer_on_system = False
        try:
            if shutil.which("gst-launch-1.0") is not None:
                gstreamer_on_system = True
        except Exception as e:
            logger.error("Error while checking system for GStreamer: %s", e)

        return gstreamer_in_cv2, gstreamer_on_system

    @staticmethod
    def gstreamer_available():
        gstreamer_cv2, gstreamer_system = GStreamerService.check_gstreamer()
        return gstreamer_cv2 and gstreamer_system

    @staticmethod
    def setup_pipeline(
        device: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        pixel_format: Optional[str] = None,
        media_type: Optional[str] = None,
    ) -> str:

        if width is None or height is None or fps is None or pixel_format is None:

            width = width
            height = height
            pixel_format = pixel_format

        fps = int(fps) if fps else None

        return (
            GstreamerPipelineBuilder()
            .device(device)
            .media_type(media_type)
            .fps(fps)
            .height(height)
            .width(width)
            .pixel_format(pixel_format)
            .build()
        )

    @staticmethod
    def list_video_devices() -> List[DeviceType]:
        """
        Cached method for enumerating video devices using GStreamer.

        This method computes the state of video devices via a checksum derived from `/dev/video*`
        and leverages a cached backend function to avoid redundant
        computations. The checksum ensures that the cache is invalidated dynamically whenever
        the state of `/dev/video*` changes (e.g., when a device is added or removed).

        Details:
        - First call after an application start or a state change triggers the enumeration of
          devices and caches the result for subsequent calls.
        - Subsequent calls with the same device state retrieve results from the cache, avoiding
          recomputation.
        - If the state of `/dev/video*` files changes, the checksum changes, invalidating the cache,
          and triggering re-enumeration.

        Returns:
        --------
        A list of DeviceType objects (`DiscreteDevice` or `DeviceStepwise`) describing
        video devices detected by GStreamer with their capabilities.
        """

        checksum = get_dev_video_checksum()
        return GStreamerService._list_video_devices(checksum)

    @staticmethod
    @lru_cache(maxsize=None)
    def _list_video_devices(_: str) -> List[DeviceType]:
        """
        Low-level, cached method to enumerate video source devices using GStreamer.

        This method uses GStreamer’s native getters (e.g. Gst.Structure and Gst.Caps) to
        enumerate video devices and build `DeviceType` objects (`DiscreteDevice` or `DeviceStepwise`),
        which is expensive operation.

        The ignored argument _ is the checksum that ensures that the cache is
        invalidated dynamically when any video device is added, removed, or updated on
        the system.

        Cache Behavior:
        - Results of this method are dynamically cached leveraging the `lru_cache` decorator.
        - The key to the cache is a checksum generated from the `/dev/video*` files.
        - Cache invalidates automatically when the checksum changes, signaling a device state change.

        Notes:
        - Invalid or insufficient devices (e.g., those without properties or capabilities) are
          skipped silently.
        - For better performance in the application, avoid calling this function directly. Instead,
          use `list_video_devices`, which handles checksum generation and cache management.

        Returns:
        --------
        A list of DeviceType objects (`DiscreteDevice` or `DeviceStepwise`) describing
        video devices detected by GStreamer with their capabilities.
        """
        try:
            import gi

            gi.require_version("Gst", "1.0")
            from gi.repository import Gst  # type: ignore

            Gst.init(None)
        except Exception:
            logger.warning("Failed to import 'gi'")
            return []

        monitor: Gst.DeviceMonitor = Gst.DeviceMonitor.new()

        monitor.add_filter("Video/Source", None)
        monitor.start()

        devices: List[Gst.Device] = monitor.get_devices() or []
        results: List[DeviceType] = []

        for dev in devices:
            display_name = dev.get_display_name() or "Unknown"
            props_obj = dev.get_properties()
            if props_obj is None:
                continue

            object_path = props_obj.get_string("object.path")
            logger.debug(
                "object_path='%s', display_name='%s'",
                object_path,
                display_name,
            )

            if object_path is None:
                continue

            api, path = GStreamerParser.parse_device_path(object_path)

            logger.debug("api='%s', path=%s", api, path)

            caps_obj = dev.get_caps()
            if not caps_obj or caps_obj.get_size() == 0:
                continue

            for i in range(caps_obj.get_size()):
                structure = caps_obj.get_structure(i)
                media_type = structure.get_name()

                pixel_format = structure.get_string("format")
                logger.debug(
                    "pixel_format='%s', media_type='%s'", pixel_format, media_type
                )
                common = {
                    "name": display_name,
                    "device": object_path,
                    "api": api,
                    "path": path,
                    "media_type": media_type,
                    "pixel_format": pixel_format if pixel_format else None,
                }

                ok_w, width = structure.get_int("width")
                ok_h, height = structure.get_int("height")
                ok_f, num, den = structure.get_fraction("framerate")
                logger.debug("num=%s, den=%s, ok_f=%s", num, den, ok_f)

                if ok_f and ok_w and ok_h:
                    fps = float(num) / float(den)
                    device_obj = DiscreteDevice(
                        **common, width=width, height=height, fps=fps
                    )
                    results.append(device_obj)
                elif ok_w and ok_h:
                    rate_val = None
                    try:
                        rate_val = structure.get_value("framerate")
                    except Exception:
                        pass
                    if rate_val and isinstance(rate_val, (list, tuple)):
                        for fraction in rate_val:
                            try:
                                # each fraction might be a Gst.Fraction or a tuple with numerator and denominator.
                                num = getattr(fraction, "numerator", None)
                                den = getattr(fraction, "denominator", None)
                                if num is None or den is None:
                                    # Try assuming it's a tuple.
                                    num, den = fraction
                                fps = float(num) / float(den)
                                device_obj = DiscreteDevice(
                                    **common, width=width, height=height, fps=fps
                                )
                                results.append(device_obj)
                            except Exception as e:
                                logger.error(
                                    "Error processing framerate fraction: %s", e
                                )
                    else:
                        struct_str = structure.to_string()
                        fractions_fps = GStreamerParser.parse_framerate(struct_str)
                        if fractions_fps:
                            for fps in fractions_fps:
                                device_obj = DiscreteDevice(
                                    **common, width=width, height=height, fps=fps
                                )
                                results.append(device_obj)
                        else:
                            device_obj = DiscreteDevice(
                                **common,
                                width=width,
                                height=height,
                            )
                            results.append(device_obj)
                else:

                    ok_min_w, min_width = structure.get_int("min_width")
                    ok_max_w, max_width = structure.get_int("max_width")
                    ok_min_h, min_height = structure.get_int("min_height")
                    ok_max_h, max_height = structure.get_int("max_height")
                    ok_min_f, min_num, min_den = structure.get_fraction("min_fps")
                    ok_max_f, max_num, max_den = structure.get_fraction("max_fps")
                    if (
                        ok_min_w
                        and ok_max_w
                        and ok_min_h
                        and ok_max_h
                        and ok_min_f
                        and ok_max_f
                        and min_den != 0
                        and max_den != 0
                    ):
                        try:
                            min_fps = float(min_num) / float(min_den)
                            max_fps = float(max_num) / float(max_den)
                            device_obj = DeviceStepwise(
                                **common,
                                min_width=min_width,
                                max_width=max_width,
                                min_height=min_height,
                                max_height=max_height,
                                min_fps=min_fps,
                                max_fps=max_fps,
                                width_step=1,
                                height_step=1,
                                fps_step=1,
                            )
                            results.append(device_obj)
                        except Exception:
                            pass

        monitor.stop()
        logger.debug("gstreamer devices %s", results)
        return results


if __name__ == "__main__":
    devices = GStreamerService.list_video_devices()
    if not devices:
        print("No valid video devices found.")
    else:
        print("Valid video devices:")
        for dev in devices:
            print(dev.model_dump())
