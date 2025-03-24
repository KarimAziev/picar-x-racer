"""
V4L2_service.py

This service uses low-level ioctls (via fcntl and Python’s ctypes binding to v4l2)
to enumerate available camera device formats. In this implementation, a mode is
classified as “discrete” if the framesize ioctl returns V4L2_FRMSIZE_TYPE_DISCRETE,
or “stepwise/continuous” if the enumerated structure contains a range with steps.

Note:
  For discrete resolution, there may be multiple fps (frame interval) options –
  in that case we create one configuration per fps.
"""

import ctypes
import fcntl
import os
import re
from functools import lru_cache
from typing import List, Optional, Set, Union, cast

from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.core.video_device_abc import VideoDeviceABC
from app.schemas.camera import DeviceStepwise, DeviceType, DiscreteDevice
from app.types.v4l2_types import (
    ContinuousFrameSizeConfig,
    DiscreteFrameIntervalConfig,
    DiscreteFrameSizeConfig,
    PixelFormatConfig,
    StepwiseFrameIntervalConfig,
    StepwiseFrameSizeConfig,
    VideoCaptureFormat,
)
from app.util.fd_utils import fd_open
from app.util.video_checksum import get_dev_video_checksum
from v4l2 import (
    _IOWR,
    V4L2_BUF_TYPE_VIDEO_CAPTURE,
    V4L2_FRMIVAL_TYPE_CONTINUOUS,
    V4L2_FRMIVAL_TYPE_DISCRETE,
    V4L2_FRMIVAL_TYPE_STEPWISE,
    V4L2_FRMSIZE_TYPE_CONTINUOUS,
    V4L2_FRMSIZE_TYPE_DISCRETE,
    V4L2_FRMSIZE_TYPE_STEPWISE,
    VIDIOC_ENUM_FMT,
    VIDIOC_ENUM_FRAMEINTERVALS,
    VIDIOC_ENUM_FRAMESIZES,
    VIDIOC_G_FMT,
    VIDIOC_QUERYCAP,
    v4l2_capability,
    v4l2_fmtdesc,
    v4l2_format,
    v4l2_frmivalenum,
    v4l2_frmsize_discrete,
)


# original library didn't specify max_width in v4l2_frmsize_stepwise
class v4l2_frmsize_stepwise(ctypes.Structure):
    _fields_ = [
        ("min_width", ctypes.c_uint32),
        ("max_width", ctypes.c_uint32),
        ("step_width", ctypes.c_uint32),
        ("min_height", ctypes.c_uint32),
        ("max_height", ctypes.c_uint32),
        ("step_height", ctypes.c_uint32),
    ]


class v4l2_frmsizeenum(ctypes.Structure):
    class _u(ctypes.Union):
        _fields_ = [
            ("discrete", v4l2_frmsize_discrete),
            ("stepwise", v4l2_frmsize_stepwise),
        ]

    _fields_ = [
        ("index", ctypes.c_uint32),
        ("pixel_format", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("_u", _u),
        ("reserved", ctypes.c_uint32 * 2),
    ]

    _anonymous_ = ("_u",)


VIDIOC_ENUM_FRAMESIZES = _IOWR("V", 74, v4l2_frmsizeenum)

logger = Logger(__name__)


class V4L2Service(VideoDeviceABC, metaclass=SingletonMeta):
    def __init__(self):
        self.failed_devices: Set[str] = set()
        self.succeed_devices: Set[str] = set()

    @staticmethod
    def fourcc_to_str(fourcc: int) -> str:
        """
        Returns the string representation of a FOURCC code.
        """
        return "".join(chr((fourcc >> (8 * i)) & 0xFF) for i in range(4))

    def list_video_devices(self) -> List[DeviceType]:
        """
        High-level public method to list video devices with caching.
        Checks the checksum of `/dev/video*` to determine if reevaluation is necessary.

        Returns:
        --------
        A list of device configurations for all video devices.
        """
        checksum = get_dev_video_checksum()
        return self._cached_list_video_devices(checksum)

    def video_capture_format(self, device_path: str) -> Optional[VideoCaptureFormat]:
        """
        Query the current video capture format using only low-level ioctls.

        Returns a dictionary with:
            width (int), height (int) and pixel_format (str)
        """
        fmt = v4l2_format()
        # Zero-out the struct before use
        # ctypes.memset(ctypes.byref(fmt), 0, ctypes.sizeof(fmt))
        fmt.type = V4L2_BUF_TYPE_VIDEO_CAPTURE

        try:
            with fd_open(device_path, os.O_RDWR) as fd:
                fcntl.ioctl(fd, VIDIOC_G_FMT, fmt)
        except Exception as e:
            logger.error(f"VIDIOC_G_FMT failed on {device_path}: {e}")
            return None

        width = fmt.fmt.pix.width
        height = fmt.fmt.pix.height
        pixelformat = fmt.fmt.pix.pixelformat
        pixel_format_str = self.fourcc_to_str(pixelformat)
        format_item: VideoCaptureFormat = {
            "width": width,
            "height": height,
            "pixel_format": pixel_format_str,
        }

        return format_item

    @lru_cache(maxsize=None)
    def _cached_list_video_devices(self, _: str) -> List[DeviceType]:
        """
        Cached, internal method to list video devices based on the checksum.

        The ignored argument _ is the checksum that ensures that the cache is
        invalidated dynamically when any video device is added, removed, or updated on
        the system.

        Returns:
        --------
        A list of device configurations for all video devices.
        """
        devices: List[str] = self._enumerate_video_devices()
        logger.debug("Found video devices: %s", devices)

        all_configs: List[DeviceType] = []
        for dev in devices:
            cap = self._query_capabilities(dev)
            if cap is None:
                continue
            if not (cap.capabilities & 0x00000001):
                logger.debug("%s does not support capture", dev)
                continue

            configs: List[DeviceType] = self._get_device_configurations(dev)
            all_configs.extend(configs)

        for item in all_configs:
            self.succeed_devices.add(item.device)
            if item.device in self.failed_devices:
                self.failed_devices.remove(item.device)

        return all_configs

    def _enumerate_video_devices(self) -> List[str]:
        """
        Look for devices in /dev whose name starts with 'video' (e.g. video0, video1...).
        Returns a sorted list of full device paths.
        """
        dev_dir: str = "/dev"
        devices: List[str] = []
        files = os.listdir(dev_dir)

        try:
            for name in files:
                if re.match(r"^video\d+$", name):
                    devices.append(os.path.join(dev_dir, name))
        except Exception as e:
            logger.error(f"Could not list directory {dev_dir}: {e}")
        return sorted(devices)

    def _query_capabilities(self, device_path: str) -> Optional[v4l2_capability]:
        """
        Query the device capabilities via VIDIOC_QUERYCAP.
        Returns a v4l2_capability structure on success; otherwise, None.
        """
        cap = v4l2_capability()
        try:
            with fd_open(device_path, os.O_RDWR) as fd:
                fcntl.ioctl(fd, VIDIOC_QUERYCAP, cap)
        except Exception as e:
            logger.warning(f"VIDIOC_QUERYCAP failed on {device_path}: {e}")
            return None
        return cap

    def _enumerate_formats(self, device_path: str) -> List[PixelFormatConfig]:
        """
        Enumerate the supported pixel formats using VIDIOC_ENUM_FMT.
        Returns a list of dicts with "index", "pixelformat", and "description".
        """
        formats: List[PixelFormatConfig] = []
        try:
            with fd_open(device_path, os.O_RDWR) as fd:
                index = 0
                while True:
                    fmtdesc = v4l2_fmtdesc()
                    fmtdesc.index = index
                    fmtdesc.type = V4L2_BUF_TYPE_VIDEO_CAPTURE
                    try:
                        fcntl.ioctl(fd, VIDIOC_ENUM_FMT, fmtdesc)
                    except Exception:
                        # Enumeration finished
                        break

                    # Decode the description (strip nulls)
                    desc = (
                        fmtdesc.description.decode("utf-8", errors="ignore")
                        .strip("\x00")
                        .strip()
                    )
                    formats.append(
                        {
                            "index": index,
                            "pixelformat": fmtdesc.pixelformat,
                            "description": desc,
                        }
                    )
                    index += 1
        except Exception as e:
            logger.error(f"Failed to enumerate formats on {device_path}: {e}")

        return formats

    def _enumerate_framesizes(
        self, device_path: str, pixelformat: int
    ) -> List[
        Union[
            DiscreteFrameSizeConfig, StepwiseFrameSizeConfig, ContinuousFrameSizeConfig
        ]
    ]:
        """
        Enumerate frame sizes for a given pixel format using VIDIOC_ENUM_FRAMESIZES.
        For discrete modes, returns width/height.
        For stepwise or continuous modes, returns min/max and step values.
        """
        frame_sizes: List[
            Union[
                DiscreteFrameSizeConfig,
                StepwiseFrameSizeConfig,
                ContinuousFrameSizeConfig,
            ]
        ] = []
        try:
            with fd_open(device_path, os.O_RDWR) as fd:
                index: int = 0
                while True:
                    frmsize: v4l2_frmsizeenum = v4l2_frmsizeenum()
                    frmsize.index = index
                    frmsize.pixel_format = pixelformat
                    try:
                        fcntl.ioctl(fd, VIDIOC_ENUM_FRAMESIZES, frmsize)
                    except Exception:
                        # enumeration is complete
                        break

                    if frmsize.type == V4L2_FRMSIZE_TYPE_DISCRETE:
                        discrete_config: DiscreteFrameSizeConfig = {
                            "type": "discrete",
                            "width": frmsize.discrete.width,
                            "height": frmsize.discrete.height,
                        }
                        frame_sizes.append(discrete_config)
                    elif frmsize.type == V4L2_FRMSIZE_TYPE_STEPWISE:
                        frmsize_stepwise = frmsize.stepwise
                        stepwise_config: StepwiseFrameSizeConfig = {
                            "type": "stepwise",
                            "min_width": frmsize_stepwise.min_width,
                            "max_width": frmsize_stepwise.max_width,
                            "step_width": frmsize_stepwise.step_width,
                            "min_height": frmsize_stepwise.min_height,
                            "max_height": frmsize_stepwise.max_height,
                            "step_height": frmsize_stepwise.step_height,
                        }
                        frame_sizes.append(stepwise_config)
                    elif frmsize.type == V4L2_FRMSIZE_TYPE_CONTINUOUS:
                        continuous_config: ContinuousFrameSizeConfig = {
                            "type": "continuous",
                            "min_width": frmsize.stepwise.min_width,
                            "max_width": frmsize.stepwise.max_width,
                            "min_height": frmsize.stepwise.min_height,
                            "max_height": frmsize.stepwise.max_height,
                        }
                        frame_sizes.append(continuous_config)
                    index += 1
        except Exception as e:
            logger.error(f"Failed to enumerate frame sizes on {device_path}: {e}")
        return frame_sizes

    def _enumerate_frameintervals(
        self, device_path: str, pixelformat: int, width: int, height: int
    ) -> List[Union[DiscreteFrameIntervalConfig, StepwiseFrameIntervalConfig]]:
        """
        For a specific resolution (width and height) and pixel format, enumerate frame intervals
        using VIDIOC_ENUM_FRAMEINTERVALS. Returns a list of dicts.
          - For discrete intervals, computes fps = denominator / numerator.
          - For stepwise/continuous, returns min/max and step fps.
        """
        intervals: List[
            Union[DiscreteFrameIntervalConfig, StepwiseFrameIntervalConfig]
        ] = []
        try:
            with fd_open(device_path, os.O_RDWR) as fd:
                index: int = 0
                while True:
                    frmival: v4l2_frmivalenum = v4l2_frmivalenum()
                    frmival.index = index
                    frmival.pixel_format = pixelformat
                    frmival.width = width
                    frmival.height = height
                    try:
                        fcntl.ioctl(fd, VIDIOC_ENUM_FRAMEINTERVALS, frmival)
                    except Exception:
                        break

                    if frmival.type == V4L2_FRMIVAL_TYPE_DISCRETE:
                        # Compute fps = denominator/numerator (if numerator nonzero)
                        num = frmival.discrete.numerator
                        den = frmival.discrete.denominator
                        fps = den / num if num != 0 else 0
                        intervals.append({"type": "discrete", "fps": fps})
                    elif frmival.type in (
                        V4L2_FRMIVAL_TYPE_STEPWISE,
                        V4L2_FRMIVAL_TYPE_CONTINUOUS,
                    ):
                        min_num = frmival.stepwise.min.numerator
                        min_den = frmival.stepwise.min.denominator
                        max_num = frmival.stepwise.max.numerator
                        max_den = frmival.stepwise.max.denominator
                        step_num = frmival.stepwise.step.numerator
                        step_den = frmival.stepwise.step.denominator

                        min_fps = min_den / min_num if min_num != 0 else 0
                        max_fps = max_den / max_num if max_num != 0 else 0
                        step_fps = step_den / step_num if step_num != 0 else 0
                        intervals.append(
                            {
                                "type": "stepwise",
                                "min_fps": min_fps,
                                "max_fps": max_fps,
                                "step_fps": step_fps,
                            }
                        )
                    index += 1
        except Exception as e:
            logger.error(f"Failed to enumerate frame intervals on {device_path}: {e}")
        return intervals

    def _get_device_configurations(self, device_path: str) -> List[DeviceType]:
        """
        Combines enumeration routines to collect device configurations.
        For each supported pixel format:
          • Enumerate frame sizes (resolutions)
          • For each discrete resolution, enumerate frame intervals.
            If more than one discrete interval exists, produce one configuration per fps value.
          • For stepwise/continuous modes, return one configuration that contains the min/max fps range.
        Returns a list of configuration dictionaries.
        """
        configurations: List[DeviceType] = []
        fmts: List[PixelFormatConfig] = self._enumerate_formats(device_path)
        for fmt in fmts:
            pixelfmt = cast(int, fmt["pixelformat"])
            sizes: List[
                Union[
                    DiscreteFrameSizeConfig,
                    StepwiseFrameSizeConfig,
                    ContinuousFrameSizeConfig,
                ]
            ] = self._enumerate_framesizes(device_path, pixelfmt)
            for size in sizes:
                if size.get("type") == "discrete":
                    discrete_item = cast(DiscreteFrameSizeConfig, size)
                    width = discrete_item["width"]
                    height = discrete_item["height"]
                    intervals: List[
                        Union[DiscreteFrameIntervalConfig, StepwiseFrameIntervalConfig]
                    ] = self._enumerate_frameintervals(
                        device_path, pixelfmt, width, height
                    )

                    discrete_intervals: List[DiscreteFrameIntervalConfig] = [
                        cast(DiscreteFrameIntervalConfig, i)
                        for i in intervals
                        if i.get("type") == discrete_item["type"]
                    ]
                    if discrete_intervals:
                        for interval in discrete_intervals:
                            config = {
                                "device": device_path,
                                "pixel_format_raw": pixelfmt,
                                "pixel_format": self.fourcc_to_str(pixelfmt),
                                "format_desc": fmt["description"],
                                "mode_type": "discrete",
                                "width": width,
                                "height": height,
                                "fps": interval["fps"],
                            }
                            configurations.append(DiscreteDevice(**config))

                    else:
                        self.failed_devices.add(device_path)

                elif size.get("type") in ("stepwise", "continuous"):
                    # For stepwise and continuous modes, we use the minimum resolution to query fps range.
                    item = cast(
                        Union[
                            StepwiseFrameSizeConfig,
                            ContinuousFrameSizeConfig,
                        ],
                        size,
                    )
                    min_w = item.get("min_width")
                    min_h = item.get("min_height")
                    w_step = item.get("step_width")  # might be None for continuous
                    h_step = item.get("step_height")  # might be None for continuous
                    pixel_format_str = self.fourcc_to_str(pixelfmt)
                    config = {
                        "device": device_path,
                        "pixel_format_raw": pixelfmt,
                        "pixel_format": pixel_format_str,
                        "format_desc": fmt["description"],
                        "mode_type": size["type"],
                        "min_width": min_w,
                        "max_width": size.get("max_width"),
                        "min_height": min_h,
                        "max_height": size.get("max_height"),
                    }

                    if w_step is not None:
                        config["width_step"] = int(w_step)
                    if h_step is not None:
                        config["height_step"] = int(h_step)

                    intervals = self._enumerate_frameintervals(
                        device_path, pixelfmt, min_w, min_h
                    )
                    if intervals:
                        discrete_intervals = [
                            cast(DiscreteFrameIntervalConfig, i)
                            for i in intervals
                            if i.get("type") == "discrete"
                        ]
                        if discrete_intervals:
                            # Use the lowest and highest fps from the discrete list.
                            config["min_fps"] = discrete_intervals[0]["fps"]
                            config["max_fps"] = discrete_intervals[-1]["fps"]

                            config["fps_step"] = (
                                discrete_intervals[-1]["fps"]
                                - discrete_intervals[0]["fps"]
                                if len(discrete_intervals) > 1
                                else 1
                            )
                        else:
                            step_info: StepwiseFrameIntervalConfig = cast(
                                StepwiseFrameIntervalConfig, intervals[0]
                            )
                            config["min_fps"] = step_info.get("min_fps")
                            config["max_fps"] = step_info.get("max_fps")
                            config["fps_step"] = step_info.get("step_fps", 1)
                            configurations.append(DeviceStepwise(**config))
                    else:
                        self.failed_devices.add(device_path)
        return configurations


if __name__ == "__main__":
    service = V4L2Service()
    all_configs = service.list_video_devices()

    logger.info("Result: %s", all_configs)
