import re
from typing import List, Optional, Tuple

from app.core.logger import Logger

_log = Logger(__name__)


class GStreamerParser:
    @staticmethod
    def parse_device_path(input_string: str) -> Tuple[Optional[str], str]:
        """
        If the object path has an api prefix (like "v4l2:/dev/video0"),
        return a tuple (api, path); otherwise, return (None, device_path)
        """
        match = re.match(r"([^:]+):(/.*)", input_string)
        if match:
            part1 = match.group(1)
            part2 = match.group(2)
            return part1, part2
        else:
            return None, input_string

    @staticmethod
    def strip_api_prefix(input_string: str) -> str:
        """
        Return device path without api prefix (e.g. "v4l2:" in "v4l2:/dev/video0").

        If the input string doesn't have an api prefix, return it as is.

        Example:

        ```python
        strip_api_prefix("v4l2:/dev/video0") ;; -> "/dev/video0"
        strip_api_prefix("/dev/video0") ;; -> "/dev/video0"
        strip_api_prefix("libcamera:/base/soc/i2c0mux/i2c@1/imx708@1a") ;; -> "/base/soc/i2c0mux/i2c@1/imx708@1a"
        ```

        """
        _, path = GStreamerParser.parse_device_path(input_string)
        return path

    @staticmethod
    def parse_framerate(struct_str: str) -> List[float]:
        """
        Parse the framerate information from a GStreamer structure string.

        It supports two primary formats commonly found in GStreamer structure definitions:

        1. `framerate={ (fraction)15/1, (fraction)30/1 }`
        2. `framerate=(fraction){ 15/1, 30/1 }`

        The extracted fractions are converted to their floating-point
        representations (e.g., `15/1 -> 15.0`, `30/1 -> 30.0`).

        Example Usage:
        --------------
        ```python
        struct_str = "framerate=(fraction){ 15/1, 30/1 }"
        fps_values = GStreamerParser.parse_framerate(struct_str)
        print(fps_values)  # Output: [30.0, 15.0]
        ```

        Parameters:
        --------------
        struct_str
            A GStreamer structure string containing framerate definitions.

        Returns:
        --------------
        A deduplicated, descending-sorted list of frame rates extracted
        from the input string, represented as floating-point values.

        Notes:
        --------------
        - If no valid frame rates are found in the input string, an empty list
          is returned.
        - Logs any parsing errors or issues with invalid fractions.
        """
        fps_results: set[float] = set()

        # handling such format "framerate={ (fraction)15/1, (fraction)30/1 }"
        if fractions := re.findall(r"\(fraction\)\s*([0-9]+/[0-9]+)", struct_str):
            for frac in fractions:
                try:
                    num_str, den_str = frac.split("/")
                    num = int(num_str)
                    den = int(den_str)
                    fps = float(num) / float(den)
                    fps_results.add(fps)
                except Exception as e:
                    _log.error("Error processing fraction '%s': %s", frac, e)

        # handling such format "framerate=(fraction){ 15/1, 30/1 }"
        elif framerate_match := re.search(
            r"framerate=\(fraction\)\{?\s*([^}]*)\}?", struct_str
        ):
            frac_list_str = framerate_match.group(1)
            fractions = re.findall(r"([0-9]+/[0-9]+)", frac_list_str)
            if fractions:
                for frac_str in fractions:
                    try:
                        num_str, den_str = frac_str.split("/")
                        num = int(num_str)
                        den = int(den_str)
                        fps = float(num) / float(den)
                        fps_results.add(fps)
                    except Exception as e:
                        _log.error(
                            "Error processing fraction '%s': %s",
                            frac_str,
                            e,
                        )
            else:
                _log.warning(
                    "No valid fractions found in framerate group: %s",
                    frac_list_str,
                )

        return sorted(fps_results, reverse=True)
