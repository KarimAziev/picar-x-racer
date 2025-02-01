import re
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from app.core.logger import Logger
from app.schemas.camera import DeviceStepwiseBase, DiscreteDevice

logger = Logger(__name__)


class V4L2FormatParser:
    """
    Parses the `v4l2-ctl --list-formats-ext` output and produces a list of formats.

    Handles both discrete and stepwise resolutions with corresponding frame rates.
    """

    FORMAT_PATTERN = re.compile(r"\[\d+\]: '([A-Z0-9]+)' \((.+)\)")
    RESOLUTION_DISCRETE_PATTERN = re.compile(r"Size: Discrete (\d+)x(\d+)")
    RESOLUTION_STEPWISE_PATTERN = re.compile(
        r"Size: Stepwise (\d+)x(\d+) - (\d+)x(\d+) with step (\d+)/(\d+)"
    )
    FPS_PATTERN = re.compile(r"Interval: Discrete [0-9.]+s \((\d+)\.000 fps\)")

    def __init__(self, device: str, name: Optional[str] = None):
        self.device = device
        self.name = name
        self.formats: List[Union[DeviceStepwiseBase, DiscreteDevice]] = []
        self.current_pixel_format: Optional[str] = None
        self.last_resolution: Optional[Dict[str, Any]] = None

    def parse(self, output: str) -> List[Union[DeviceStepwiseBase, DiscreteDevice]]:
        """Parses the raw `v4l2-ctl` output to return a flat list of formats."""
        lines = output.splitlines()

        for line in lines:
            self._process_line(line.strip())

        return self.formats

    def _process_line(self, line: str) -> None:
        if not line:
            return

        try:
            if format_match := self.FORMAT_PATTERN.match(line):
                self.current_pixel_format = format_match.group(1)

            elif discrete_match := self.RESOLUTION_DISCRETE_PATTERN.match(line):
                width, height = int(discrete_match.group(1)), int(
                    discrete_match.group(2)
                )
                self._start_discrete_resolution(width, height)

            elif stepwise_match := self.RESOLUTION_STEPWISE_PATTERN.match(line):
                groups = stepwise_match.groups()
                groups = cast(Tuple[str, str, str, str, str, str], groups)
                self._process_stepwise_resolution(groups)

            elif fps_match := self.FPS_PATTERN.search(line):
                fps = int(fps_match.group(1))
                self._add_fps_to_last_resolution(fps)

        except Exception:
            logger.error(f"Unexpected parsing error for line: {line}", exc_info=True)

    def _start_discrete_resolution(self, width: int, height: int):
        """Stores discrete resolutions for the current pixel format."""
        self.last_resolution = {
            "device": self.device,
            "width": width,
            "height": height,
            "pixel_format": self.current_pixel_format,
            "name": self.name,
        }

    def _add_fps_to_last_resolution(self, fps: int):
        """Creates a new entry for the current discrete resolution and FPS."""
        if self.last_resolution:
            self.formats.append(DiscreteDevice(**{**self.last_resolution, "fps": fps}))

    def _process_stepwise_resolution(self, groups: Tuple[str, str, str, str, str, str]):
        """Stores stepwise resolutions for the current pixel format."""
        min_width, min_height = int(groups[0]), int(groups[1])
        max_width, max_height = int(groups[2]), int(groups[3])
        width_step, height_step = int(groups[4]), int(groups[5])
        data = DeviceStepwiseBase(
            **{
                "name": self.name,
                "device": self.device,
                "pixel_format": self.current_pixel_format,
                "min_width": min_width,
                "max_width": max_width,
                "min_height": min_height,
                "max_height": max_height,
                "width_step": width_step,
                "height_step": height_step,
            }
        )

        self.formats.append(data)

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
