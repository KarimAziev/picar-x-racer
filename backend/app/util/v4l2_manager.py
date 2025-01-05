import os
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from app.util.logger import Logger
from app.util.v4l2_parser import V4L2FormatParser

logger = Logger(__name__)

CameraInfo = Tuple[str, str]


class V4L2:
    @staticmethod
    def list_video_devices_with_formats() -> List[Dict[str, Any]]:
        """
        List available video devices along with their supported formats.

        Each device's formats are structured hierarchically, with the device
        as the parent and its formats as children.

        Returns:
            A list of dictionaries where each dictionary represents a video device
            and its supported formats. The structure of the dictionary is as
            follows:
                - key: The video device key (e.g., `/dev/video0`).
                - label: A human-readable label for the device.
                - children: A list of dictionaries representing
                  the supported video formats of the device.

        Example:
            ```python
            devices = list_video_devices_with_formats()
            print(devices)
            # Output example:
            # [
            #     {
            #         "key": "/dev/video0",
            #         "label": "/dev/video0 (Integrated Camera)",
            #         "children": [
            #             {... video formats for /dev/video0 ...}
            #         ],
            #     },
            #     {
            #         "key": "/dev/video1",
            #         "label": "/dev/video1",
            #         "children": [
            #             {... video formats for /dev/video1 ...}
            #         ],
            #     },
            # ]
            ```
        """
        result: List[Dict[str, Any]] = []
        for key, category in V4L2.list_camera_devices():
            formats = V4L2.list_device_formats_ext(key)
            if formats:
                item = {
                    "key": key,
                    "label": f"{key} ({category})" if category is not None else key,
                    "children": formats,
                }
                result.append(item)

        return result

    @staticmethod
    def list_camera_devices() -> List[CameraInfo]:
        """
        Retrieves a list of available camera devices.

        Parses the output from `v4l2_list_devices` to extract camera paths and their respective categories.
        Returns the primary camera for each category first, followed by secondary cameras. If no cameras are found,
        falls back to listing potential camera devices based on video files in /dev/.

        Returns:
            A list of tuples, each containing a device path and a category, representing available cameras.
            If no category is found, the category string is empty.
        """
        lines = V4L2.v4l2_list_devices()
        category_pattern = re.compile(r"^(.+) \(.+\):$")
        video_device_pattern = re.compile(r"^(\s+)(/dev/video\d+)$")
        primary_cameras: List[CameraInfo] = []
        secondary_cameras: List[CameraInfo] = []

        current_category: Optional[str] = None
        current_category_primary_initted = False

        for line in lines:
            category_match = category_pattern.match(line)
            if category_match:
                current_category = category_match.group(1).strip()
                current_category_primary_initted = False
            else:
                video_device_match = video_device_pattern.match(line)
                if video_device_match and current_category:
                    video_device = video_device_match.group(2).strip()
                    if video_device and isinstance(video_device, str):
                        pair = (video_device, current_category)
                        if current_category_primary_initted:
                            secondary_cameras.append(pair)
                        else:
                            current_category_primary_initted = True
                            primary_cameras.append(pair)

        result = primary_cameras + secondary_cameras
        if len(result) >= 1:
            return result

        dev_video_files = sorted(
            [
                f"/dev/{dev}"
                for dev in os.listdir("/dev")
                if re.match(r"video[0-9]+", dev)
            ]
        )
        return [(device, "") for device in dev_video_files]

    @staticmethod
    def list_device_formats_ext(device: str) -> List[Dict[str, Any]]:
        """
        Retrieve extended video format details for a specific video device.

        This function runs the `v4l2-ctl --list-formats-ext` command on the specified
        video device to query its format capabilities. The output is parsed and
        organized into a list of dictionaries that describe each format, resolution,
        and frame rate supported by the device.

        Args:
            device (str): The video device identifier (e.g., `/dev/video0`).

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the supported
            video formats. Each dictionary describes a format or resolution in a
            hierarchical structure.

        Example:
            ```python
            formats = list_device_formats_ext("/dev/video0")
            print(formats)
            # Output example:
            # [
            #     {
            #         "key": "/dev/video0:YUYV",
            #         "label": "YUYV",
            #         "children": [
            #             {... resolutions and frame rates for YUYV format ...}
            #         ],
            #     },
            #     ...
            # ]
            ```
        """
        try:
            cmd = ["v4l2-ctl", "--list-formats-ext", "--device", device]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing v4l2-ctl: {e}")
            return []

        parser = V4L2FormatParser(device)

        return parser.parse(output)

    @staticmethod
    def v4l2_list_devices() -> List[str]:
        """
        Lists V4L2 video capture devices on the system.

        Uses the `v4l2-ctl` command-line utility to get details about available
        video capture devices on the system and returns the raw output lines.

        Returns:
           A list of output lines from the `v4l2-ctl --list-devices` command.
        """
        lines = []
        try:
            result = subprocess.run(
                ["v4l2-ctl", "--list-devices"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            lines = result.stdout.strip().splitlines()

        except subprocess.CalledProcessError as e:
            logger.error("Failed to run 'v4l2-ctl --list-devices':", e)

        except Exception:
            logger.error("Unexpected exception occurred: ", exc_info=True)

        return lines

    @staticmethod
    def find_device_info(device: str) -> Optional[CameraInfo]:
        """
        Finds the device info of a specific camera device from the list of available camera devices.

        Searches for the given device in the list of available camera devices and
        returns its associated information (e.g., device path and category).

        Args:
            device: The path to the camera device (e.g., `/dev/video0`).

        Returns:
            A tuple containing the device path and its category if the device is found, otherwise `None`.
        """
        devices = V4L2.list_camera_devices()
        for device_path, device_info in devices:
            if device_path == device:
                return (device, device_info)

    @staticmethod
    def video_capture_format(device: str) -> Dict[str, Any]:
        """
        Query the video capture format for the specified device.

        Args:
            device (str): The path to the camera device, e.g., '/dev/video0'.
            category (str): The camera type or category for labeling purposes.

        Returns:
            a dictionary with:
              width: int
              height: int
              pixel_format: str
        """
        try:
            cmd = ["v4l2-ctl", "-V", "--device", device]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing v4l2-ctl: {e}")
            return {}

        return V4L2.parse_v4l2_device_info_output(output)

    @staticmethod
    def parse_v4l2_device_info_output(output: str) -> Dict[str, Any]:
        """
        Parse the output of v4l2-ctl --V --device for the specified device.

        Args:
            output (str): the output of 'v4l2-ctl --V --device DEVICE', e.g.:
        Format Video Capture:
            Width/Height      : 800/600
            Pixel Format      : 'MJPG' (Motion-JPEG)
            Field             : None
            Bytes per Line    : 0
            Size Image        : 486400
            Colorspace        : SMPTE 170M
            Transfer Function : Default (maps to Rec. 709)
            YCbCr/HSV Encoding: Default (maps to ITU-R 601)
            Quantization      : Default (maps to Full Range)
            Flags

        Returns:
            a dictionary with:
              width: int
              height: int
              pixel_format: str
        """
        width_height_regex = re.search(r"Width/Height\s+:\s+(\d+)/(\d+)", output)
        pixel_format_regex = re.search(r"Pixel Format\s+:\s+'(\w+)'", output)

        if not width_height_regex or not pixel_format_regex:
            logger.error("Failed to parse the required fields from v4l2-ctl output.")
            return {}

        width = int(width_height_regex.group(1))
        height = int(width_height_regex.group(2))
        pixel_format = pixel_format_regex.group(1)

        return {"width": width, "height": height, "pixel_format": pixel_format}
