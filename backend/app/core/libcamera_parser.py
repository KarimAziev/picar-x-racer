import re
import subprocess
from functools import lru_cache
from typing import Any, Dict, List

from app.core.logger import Logger

logger = Logger(__name__)


class LibcameraParser:
    @staticmethod
    def list_libcamera_cameras() -> List[Dict[str, Any]]:
        """
        List cameras available via the libcamera stack.
        """
        try:
            cmd = ["libcamera-still", "--list-cameras"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = result.stdout
        except FileNotFoundError as e:
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing libcamera-still: {e}")
            return []

        return LibcameraParser.parse_libcamera_list_output(output)

    @staticmethod
    @lru_cache(maxsize=128)
    def is_libcamera_device(video_path: str) -> bool:
        devices = LibcameraParser.list_libcamera_cameras()
        for item in devices:
            if item.get("key") == video_path:
                return True
        return False

    @staticmethod
    def parse_libcamera_list_output(output: str) -> List[Dict[str, Any]]:
        """
        Parse the output from `libcamera-still --list-cameras` and structure it
        in a way compatible with the existing V4L2 parser.

        Returns:
            A list of dictionaries representing libcamera-supported devices and modes.
        """
        cameras = []
        current_camera = None
        current_pixel_format = None

        for line in output.splitlines():
            line = line.strip()

            camera_header_match = re.match(r"^(\d+) : ([\w_]+) \[([^\]]+)\]", line)
            if camera_header_match:
                camera_id, name, resolution_info = camera_header_match.groups()
                current_camera = {
                    "key": f"/dev/video{camera_id}",
                    "label": f"{name} ({resolution_info})",
                    "device": name,
                    "children": [],
                }
                cameras.append(current_camera)
                continue

            mode_format_match = re.match(r"^Modes: '([\w\d_]+)' :", line)
            if mode_format_match:
                current_pixel_format = mode_format_match.group(1)
                continue

            mode_match = re.match(r"^(\d+)x(\d+) \[(\d+\.\d+) fps", line)
            if mode_match and current_camera and current_pixel_format:
                resolution = (int(mode_match.group(1)), int(mode_match.group(2)))
                fps = float(mode_match.group(3))

                current_camera["children"].append(
                    {
                        "key": f"{current_camera['device']}:{current_pixel_format}:{resolution[0]}x{resolution[1]}:{fps}",
                        "label": f"{current_pixel_format} {resolution[0]}x{resolution[1]}, {fps} fps",
                        "device": current_camera["device"],
                        "pixel_format": current_pixel_format,
                        "min_width": resolution[0],
                        "max_width": resolution[0],
                        "min_height": resolution[1],
                        "max_height": resolution[1],
                        "width_step": 1,
                        "height_step": 1,
                        "min_fps": fps,
                        "max_fps": fps,
                    }
                )

        return cameras
