import re
import subprocess
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from app.core.logger import Logger

logger = Logger(__name__)


class V4L2FormatParser:
    """
    A parser for interpreting the output of `v4l2-ctl --list-formats-ext` for a video device.

    Example with discrete resolution size:
    --------------
    ```python
    V4L2FormatParser("/dev/video2").parse(
        "ioctl: VIDIOC_ENUM_FMT\\\\n"
        "	Type: Video Capture\\\\n"
        "\\\\n"
        "	[0]: 'GREY' (8-bit Greyscale)\\\\n"
        "		Size: Discrete 640x360\\\\n"
        "			Interval: Discrete 0.067s (15.000 fps)\\\\n"
        "			Interval: Discrete 0.033s (30.000 fps)\\\\n",
    )

    # Result:
    # [
    #     {
    #         'key': '/dev/video2:GREY:640x360',
    #         'label': 'GREY, 640x360',
    #         'children': [
    #             {
    #                 'device': '/dev/video2',
    #                 'width': 640,
    #                 'height': 360,
    #                 'pixel_format': 'GREY',
    #                 'key': '/dev/video2:GREY:640x360:15',
    #                 'label': 'GREY, 640x360, 15 fps',
    #                 'fps': 15,
    #             },
    #             {
    #                 'device': '/dev/video2',
    #                 'width': 640,
    #                 'height': 360,
    #                 'pixel_format': 'GREY',
    #                 'key': '/dev/video2:GREY:640x360:30',
    #                 'label': 'GREY, 640x360, 30 fps',
    #                 'fps': 30,
    #             },
    #         ],
    #     }
    # ]
    ```

    Example with both discrete and stepwise resolution sizes:
    --------------
    ```python
    V4L2FormatParser("/dev/video1").parse(
        "        [0]: 'YUYV' (YUYV 4:2:2)\\\\n"
        "            Size: Discrete 640x480\\\\n"
        "                Interval: Discrete 0.033s (30.000 fps)\\\\n"
        "        [1]: 'MJPG' (Motion-JPEG)\\\\n"
        "            Size: Stepwise 320x240 - 1280x720 with step 16/16\\\\n",
    )

    # Result:
    # [
    #     {
    #         'key': '/dev/video1:YUYV:640x480:30',
    #         'label': 'YUYV, 640x480, 30 fps',
    #         'device': '/dev/video1',
    #         'width': 640,
    #         'height': 480,
    #         'fps': 30,
    #         'pixel_format': 'YUYV',
    #     },
    #     {
    #         'key': '/dev/video1:MJPG:320x240 - 1280x720',
    #         'label': 'MJPG 320x240 - 1280x720',
    #         'device': '/dev/video1',
    #         'pixel_format': 'MJPG',
    #         'min_width': 320,
    #         'max_width': 1280,
    #         'min_height': 240,
    #         'max_height': 720,
    #         'height_step': 16,
    #         'width_step': 16,
    #         'min_fps': 90,
    #         'max_fps': 1,
    #     },
    # ]
    ```
    """

    FORMAT_PATTERN = re.compile(r"\[\d+\]: '([A-Z0-9]+)' \((.+)\)")
    RESOLUTION_DISCRETE_SIZE_PATTERN = re.compile(r"Size: Discrete (\d+x\d+)")
    RESOLUTION_STEPWISE_PATTERN = re.compile(
        r"Size: Stepwise (\d+x\d+) - (\d+x\d+) with step (\d+)/(\d+)"
    )
    DISCRETE_FPS_PATTERN = re.compile(
        r"Interval: Discrete ([0-9.]+)s \((\d+)\.000 fps\)"
    )

    def __init__(self, device: str):
        self.device = device
        self.formats = []
        self.current_pixel_format: Optional[str] = None
        self.current_pixel_format_data = {"children": []}
        self.frame_size = None

        self.discrete_size_item: Optional[Dict[str, Any]] = None
        self.discrete_size_common_data: Optional[Dict[str, Any]] = None
        self.discrete_fps_match: Optional[re.Match] = None

    def parse(self, output: str) -> List[Dict[str, Any]]:
        """
        Parse the raw `v4l2-ctl --list-formats-ext` output and
        return a hierarchical list of formats.

        It extracts the available pixel formats, supported frame sizes (both
        discrete and stepwise), and frame rates for each resolution, organizing the
        data into a hierarchical structure.

        Returns:
        A list of dictionaries representing the video format capabilities.
        Each dictionary has the following structure:
            - "key" (str): A unique key for identifying the format/resolution.
            - "label" (str): A human-readable label for the format/resolution.
            - "pixel_format" (str): The pixel format (e.g., `YUYV`).
            - Other keys varying based on whether the resolution is discrete or stepwise:
                - Discrete resolution:
                    - "device" (str): The device name.
                    - "width" (int): Frame width in pixels.
                    - "height" (int): Frame height in pixels.
                    - "fps" (int): Frames per second for this resolution.
                - Stepwise resolution:
                    - "min_width" (int): Minimum frame width in pixels.
                    - "max_width" (int): Maximum frame width in pixels.
                    - "min_height" (int): Minimum frame height in pixels.
                    - "max_height" (int): Maximum frame height in pixels.
                    - "width_step" (int): Step size for width increments.
                    - "height_step" (int): Step size for height increments.
                    - "min_fps" (int): The minimal frame rate of the camera mode.
                    - "max_fps" (int): The maximum frame rate of the camera mode.
        """
        lines = output.splitlines()

        for line in lines:
            self._process_line(line)

        self._finalize_discrete_size_item()
        self._finalize_pixel_format()

        return self.formats

    def _process_line(self, line: str):
        line = line.strip()
        if not line:
            return

        self.discrete_fps_match = self.DISCRETE_FPS_PATTERN.search(line)
        self._finalize_discrete_size_item()
        try:
            if format_match := self.FORMAT_PATTERN.match(line):
                self._start_new_pixel_format(format_match.group(1))

            elif self.discrete_fps_match:
                self._add_fps_to_discrete_item(int(self.discrete_fps_match.group(2)))

            elif resolution_discrete_match := self.RESOLUTION_DISCRETE_SIZE_PATTERN.search(
                line
            ):
                self._start_discrete_size_item(resolution_discrete_match.group(1))

            elif resolution_stepwise_match := self.RESOLUTION_STEPWISE_PATTERN.search(
                line
            ):
                min_size = resolution_stepwise_match.group(1)
                max_size = resolution_stepwise_match.group(2)
                width_step = int(resolution_stepwise_match.group(3))
                height_step = int(resolution_stepwise_match.group(4))
                self._process_stepwise_size(
                    min_size=min_size,
                    max_size=max_size,
                    width_step=width_step,
                    height_step=height_step,
                )
        except Exception:
            logger.error("Unexpected parsing error", exc_info=True)

    def _add_fps_to_discrete_item(self, fps: int):
        """
        Add the frame-per-second (fps) to the current discrete resolution item,
        creating a hierarchical child structure where each fps value corresponds
        to a specific resolution for the video format.
        """
        if self.discrete_size_item and self.discrete_size_common_data:
            value = f"{self.discrete_size_item['key']}:{fps}"
            label = f"{self.discrete_size_item['label']}, {fps} fps"
            self.discrete_size_item["children"].append(
                {
                    **self.discrete_size_common_data,
                    "key": value,
                    "label": label,
                    "fps": fps,
                }
            )
            self.discrete_fps_match = None

    def _process_stepwise_size(
        self, min_size: str, max_size: str, height_step: int, width_step: int
    ):
        """
        Handles stepwise resolution sizes by parsing and organizing `v4l2-ctl` output.
        """
        min_width, min_height = map(int, min_size.split("x"))
        max_width, max_height = map(int, max_size.split("x"))

        fps_intervals = (
            self.get_fps_intervals(
                self.device,
                width=min_width,
                height=min_height,
                pixel_format=self.current_pixel_format,
            )
            if self.current_pixel_format
            else None
        )

        if fps_intervals:
            min_fps, max_fps = fps_intervals
            self.current_pixel_format_data["children"].append(
                {
                    "key": f"{self.device}:{self.current_pixel_format}:{min_size} - {max_size}",
                    "label": f"{self.current_pixel_format} {min_size} - {max_size}",
                    "device": self.device,
                    "pixel_format": self.current_pixel_format,
                    "min_width": min_width,
                    "max_width": max_width,
                    "min_height": min_height,
                    "max_height": max_height,
                    "height_step": height_step,
                    "width_step": width_step,
                    "min_fps": min_fps,
                    "max_fps": max_fps,
                }
            )

    def _start_discrete_size_item(self, frame_size: str):
        """
        Initialize a new discrete resolution item, specifying its dimensions and associated metadata.

        Args:
            frame_size: A string representing the resolution (e.g., '640x480').
        """
        width, height = map(int, frame_size.split("x"))

        size_key = f"{self.device}:{self.current_pixel_format}:{frame_size}"
        size_label = f"{self.current_pixel_format}, {frame_size}"
        self.discrete_size_item = {
            "key": size_key,
            "label": size_label,
            "children": [],
        }
        self.discrete_size_common_data = {
            "device": self.device,
            "width": width,
            "height": height,
            "pixel_format": self.current_pixel_format,
        }

    def _finalize_discrete_size_item(self):
        """Finalize and save the current discrete resolution item."""
        if (
            not self.discrete_fps_match
            and self.discrete_size_item
            and self.discrete_size_item.get("children")
        ):
            if not self.current_pixel_format_data:
                self.current_pixel_format_data = {"children": []}

            self.current_pixel_format_data["children"].append(
                self.discrete_size_item["children"][0]
                if len(self.discrete_size_item["children"]) == 1
                else self.discrete_size_item
            )
            self.discrete_size_item = None
            self.discrete_size_common_data = None

    def _start_new_pixel_format(self, pixel_format: str):
        """
        Initialize a new pixel format entry, finalizing the current one if it
        exists and preparing a new data structure for organizing resolutions for
        the specified pixel format.
        """
        self._finalize_pixel_format()
        self.current_pixel_format = pixel_format
        self.current_pixel_format_data = {
            "key": f"{self.device}:{self.current_pixel_format}",
            "label": self.current_pixel_format,
            "children": [],
        }

    def _finalize_pixel_format(self):
        """Finalize and save the current pixel format."""
        if self.current_pixel_format_data and self.current_pixel_format_data.get(
            "children"
        ):
            if len(self.current_pixel_format_data["children"]) > 1:
                self.formats.append(self.current_pixel_format_data)
            else:
                child = self.current_pixel_format_data["children"][0]
                self.formats.append(child)

    @staticmethod
    @lru_cache(maxsize=128)
    def get_fps_intervals(
        device: str, width: int, height: int, pixel_format: str
    ) -> Optional[Tuple[int, ...]]:
        """
        Retrieve the minimum and maximum frame rates (fps) supported by a device
        for a specific resolution and pixel format.

        This function uses the `v4l2-ctl --list-frameintervals` command to query
        frame interval capabilities of the video device. It parses the output and
        returns the frame rate range as a tuple.

        Args:
            device (str): The video device identifier (e.g., `/dev/video0`).
            width (int): The frame width in pixels.
            height (int): The frame height in pixels.
            pixel_format (str): The pixel format (e.g., `YUYV` or `MJPG`).

        Returns:
            Optional[Tuple[int, int]]: A tuple containing the minimum and maximum
            frame rates (fps) for the specified resolution and pixel format, or
            `None` if no information is available.

        Example:
            ```python
            fps_range = get_fps_intervals("/dev/video0", 640, 480, "YUYV")
            print(fps_range)  # Output: (30, 60)
            ```
        """
        try:
            cmd = [
                "v4l2-ctl",
                "--list-frameintervals",
                f"width={width},height={height},pixelformat={pixel_format}",
                "--device",
                device,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing v4l2-ctl: {e}")
            return None

        return V4L2FormatParser.parse_frameinterval(output)

    @staticmethod
    def parse_frameinterval(output: str) -> Optional[Tuple[int, ...]]:
        """
        Parse and filter output from ioctl: VIDIOC_ENUM_FRAMEINTERVALS
        and return a tuple of minimum and maximum fps.

        Example 1: Continuous interval
        --------------
        ```python
        result1 = parse_frameinterval_output(
            "ioctl: VIDIOC_ENUM_FRAMEINTERVALS\\\\n"
            "        Interval: Continuous 0.011s - 1.000s (1.000-90.000 fps)"
        )
        print(result1)  # Output: (1, 90)
        ```

        Example 2: Discrete interval
        --------------
        ```python
        result2 = parse_frameinterval_output(
            "ioctl: VIDIOC_ENUM_FRAMEINTERVALS\\\\n"
            "        Interval: Discrete 0.033s (30.000 fps)"
        )

        print(result2)  # Output: (30, 30)

        ```
        """

        if "Continuous" in output:
            match = re.search(r"\(([\d.]+)-([\d.]+) fps\)", output)
            if match:
                min_fps = int(float(match.group(1)))
                max_fps = int(float(match.group(2)))

                return min_fps, max_fps

        elif "Discrete" in output:
            lines = output.splitlines()
            fps_intervals: List[int] = []
            for line in lines:
                line = line.strip()
                match = re.search(r"\(([\d.]+) fps\)", line)
                if not match:
                    continue
                value = int(float(match.group(1)))
                fps_intervals.append(value)

            if len(fps_intervals) == 1:
                return (fps_intervals[0], fps_intervals[0])
            else:
                return tuple(sorted(fps_intervals))
