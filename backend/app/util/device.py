import os
import re
import subprocess
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import cv2
from app.util.logger import Logger

logger = Logger(__name__)


CameraInfo = Tuple[str, str]


def try_video_path(path: str | int) -> Optional[cv2.VideoCapture]:
    """
    Tries to open a video capture at a specified path.

    Attempts to create and read from a video capture object using OpenCV.
    If successful, returns the video capture object; otherwise, returns None.

    Parameters:
        path: The file path or device path to the video stream.

    Returns:
        The video capture object if the path is valid and readable, otherwise None.
    """
    result: Optional[bool] = None
    cap: Optional[cv2.VideoCapture] = None

    try:
        logger.debug("Trying camera %s", path)
        cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
        result, _ = cap.read()
        if not result:
            logger.debug("Camera failed %s", path)

    except Exception as err:
        logger.debug("Camera Error: %s", err)
        if cap and cap.isOpened():
            cap.release()

    return cap if result else None


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
    lines = v4l2_list_devices()
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
        [f"/dev/{dev}" for dev in os.listdir("/dev") if re.match(r"video[0-9]+", dev)]
    )
    return [(device, "") for device in dev_video_files]


def find_device_info(device: str) -> Optional[CameraInfo]:
    devices = list_camera_devices()
    for device_path, device_info in devices:
        if device_path == device:
            return (device, device_info)


def list_video_devices_with_formats() -> List[Dict[str, Any]]:
    """
    List available video devices along with their supported formats.

    Each device's formats are structured hierarchically, with the device
    as the parent and its formats as children.

    Returns:
        A list of dictionaries where each dictionary represents a video device
        and its supported formats. The structure of the dictionary is as
        follows:
            - "key" (str): The video device key (e.g., `/dev/video0`).
            - "label" (str): A human-readable label for the device. If the device
              has a category, the format is `"{key} ({category})"`, otherwise, it
              is just `"{key}"`.
            - "children" (List[Dict]): A list of dictionaries representing
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
    for key, category in list_camera_devices():
        formats = list_device_formats_ext(key)
        if formats:
            item = {
                "key": key,
                "label": f"{key} ({category})" if category is not None else key,
                "children": formats,
            }
            result.append(item)

    return result


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

    return parse_v4l2_formats_output(output, device)


def parse_v4l2_formats_output(output: str, device: str) -> List[Dict[str, Any]]:
    """
    Parses the output of `v4l2-ctl --list-formats-ext` and extracts video format,
    resolution, and frame rate information for a specified video device.

    It extracts the available pixel formats, supported frame sizes (both
    discrete and stepwise), and frame rates for each resolution, organizing the
    data into a hierarchical structure.

    Args:
        output (str): The raw string output from `v4l2-ctl --list-formats-ext`.
        device (str): The video device identifier (e.g., `/dev/video0`).

    Returns:
        List: A list of dictionaries representing the video format
        capabilities. Each dictionary has the following structure:
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

    Example:
        ```python
        parse_v4l2_formats_output(
            "        [0]: 'YUYV' (YUYV 4:2:2)\\\\n"
            "            Size: Discrete 640x480\\\\n"
            "                Interval: Discrete 0.033s (30.000 fps)\\\\n"
            "        [1]: 'MJPG' (Motion-JPEG)\\\\n"
            "            Size: Stepwise 320x240 - 1280x720 with step 16/16\\\\n",
            "/dev/video1",
        )
        ```
        The result will be:
        [
            {
                'key': '/dev/video1:YUYV:640x480:30',
                'label': 'YUYV, 640x480, 30 fps',
                'device': '/dev/video1',
                'width': 640,
                'height': 480,
                'fps': 30,
                'pixel_format': 'YUYV',
            },
            {
                'key': '/dev/video1:MJPG:320x240 - 1280x720',
                'label': 'MJPG 320x240 - 1280x720',
                'device': '/dev/video1',
                'pixel_format': 'MJPG',
                'min_width': 320,
                'max_width': 1280,
                'min_height': 240,
                'max_height': 720,
                'height_step': 16,
                'width_step': 16,
                'min_fps': 90,
                'max_fps': 1,
            },
        ]
    """
    formats = []

    format_pattern = re.compile(r"\[\d+\]: '([A-Z0-9]+)' \((.+)\)")
    resolution_discrete_size_pattern = re.compile(r"Size: Discrete (\d+x\d+)")
    resolution_stepwise_pattern = re.compile(
        r"Size: Stepwise (\d+x\d+) - (\d+x\d+) with step (\d+)/(\d+)"
    )
    fps_pattern = re.compile(r"Interval: Discrete ([0-9.]+)s \((\d+)\.000 fps\)")

    current_pixel_format: Optional[str] = None
    current_pixel_format_data = {"children": []}
    frame_size = None
    lines = output.splitlines()

    discrete_size_item: Optional[Dict[str, Any]] = None
    discrete_size_common_data: Optional[Dict[str, Any]] = None
    discrete_fps_match: Optional[re.Match] = None

    def ensure_discrete_size_item():
        nonlocal discrete_size_item, current_pixel_format_data, discrete_size_common_data
        if (
            not discrete_fps_match
            and discrete_size_item
            and discrete_size_item.get("children")
        ):
            if not current_pixel_format_data:
                current_pixel_format_data = {"children": []}

            current_pixel_format_data["children"].append(
                discrete_size_item["children"][0]
                if len(discrete_size_item["children"]) == 1
                else discrete_size_item
            )
            discrete_size_item = None
            discrete_size_common_data = None

    def ensure_current_pixel_format_append():
        if current_pixel_format_data and current_pixel_format_data.get("children"):
            if len(current_pixel_format_data["children"]) > 1:
                formats.append(current_pixel_format_data)
            else:
                child = current_pixel_format_data["children"][0]
                formats.append(child)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        discrete_fps_match = fps_pattern.search(line)
        ensure_discrete_size_item()
        try:
            if format_match := format_pattern.match(line):
                ensure_current_pixel_format_append()
                current_pixel_format = format_match.group(1)
                current_pixel_format_data = {
                    "key": f"{device}:{current_pixel_format}",
                    "label": current_pixel_format,
                    "children": [],
                }

            elif discrete_fps_match:
                fps_value = discrete_fps_match.group(2)
                if discrete_size_item and discrete_size_common_data:
                    value = f"{discrete_size_item['key']}:{fps_value}"
                    label = f"{discrete_size_item['label']}, {fps_value} fps"
                    discrete_size_item["children"].append(
                        {
                            **discrete_size_common_data,
                            "key": value,
                            "label": label,
                            "fps": int(fps_value),
                        }
                    )
                    discrete_fps_match = None

            elif resolution_discrete_match := resolution_discrete_size_pattern.search(
                line
            ):
                frame_size = resolution_discrete_match.group(1)
                [width, height] = [int(value) for value in frame_size.split("x")]

                size_key = f"{device}:{current_pixel_format}:{frame_size}"
                size_label = f"{current_pixel_format}, {frame_size}"
                discrete_size_item = {
                    "key": size_key,
                    "label": size_label,
                    "children": [],
                }
                discrete_size_common_data = {
                    "device": device,
                    "width": width,
                    "height": height,
                    "pixel_format": current_pixel_format,
                }

            elif resolution_stepwise_match := resolution_stepwise_pattern.search(line):
                min_size = resolution_stepwise_match.group(1)
                max_size = resolution_stepwise_match.group(2)
                width_step = resolution_stepwise_match.group(3)
                height_step = resolution_stepwise_match.group(4)
                [min_width, min_height] = [int(value) for value in min_size.split("x")]
                [max_width, max_height] = [int(value) for value in max_size.split("x")]

                fps_intervals = (
                    get_fps_intervals(
                        device,
                        width=min_width,
                        height=min_height,
                        pixel_format=current_pixel_format,
                    )
                    if current_pixel_format
                    else None
                )

                if fps_intervals:
                    min_fps, max_fps = fps_intervals
                    current_pixel_format_data["children"].append(
                        {
                            "key": f"{device}:{current_pixel_format}:{min_size} - {max_size}",
                            "label": f"{current_pixel_format} {min_size} - {max_size}",
                            "device": device,
                            "pixel_format": current_pixel_format,
                            "min_width": min_width,
                            "max_width": max_width,
                            "min_height": min_height,
                            "max_height": max_height,
                            "height_step": int(height_step),
                            "width_step": int(width_step),
                            "min_fps": min_fps,
                            "max_fps": max_fps,
                        }
                    )
        except Exception:
            logger.error("Unexpected parsing error", exc_info=True)

    ensure_discrete_size_item()
    ensure_current_pixel_format_append()

    return formats


def parse_v4l2_device_info(device: str):
    """
    Parse the output of v4l2-ctl --V --device for the specified device.

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

    return parse_v4l2_device_info_output(output)


def parse_v4l2_device_info_output(output: str):
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


@lru_cache(maxsize=128)
def get_fps_intervals(
    device: str, width: int, height: int, pixel_format: str
) -> Optional[Tuple[int, int]]:
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

    return parse_frameinterval(output)


def parse_frameinterval(output: str) -> Optional[Tuple[int, int]]:
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
        match = re.search(r'\(([\d.]+)-([\d.]+) fps\)', output)
        if match:
            min_fps = int(float(match.group(1)))
            max_fps = int(float(match.group(2)))

            return min_fps, max_fps

    elif "Discrete" in output:
        match = re.search(r'\(([\d.]+) fps\)', output)
        if match:
            value = int(float(match.group(1)))
            return value, value


def parse_frameinterval_output(output: str) -> List[int]:
    """
    Parse and filter output from ioctl: VIDIOC_ENUM_FRAMEINTERVALS
    and return a list of divisible by 10 frame rates as integers in descending order.

    Example 1: Continuous interval
    --------------
    ```python
    result1 = parse_frameinterval_output(
        "ioctl: VIDIOC_ENUM_FRAMEINTERVALS\\\\n"
        "        Interval: Continuous 0.011s - 1.000s (1.000-90.000 fps)"
    )
    print(result1)  # Output: [90, 80, 70, ..., 10]
    ```

    Example 2: Discrete interval
    --------------
    ```python
    result2 = parse_frameinterval_output(
        "ioctl: VIDIOC_ENUM_FRAMEINTERVALS\\\\n"
        "        Interval: Discrete 0.033s (30.000 fps)"
    )

    print(result2)  # Output: [30]

    ```
    """

    frame_rates = []
    if "Continuous" in output:
        match = re.search(r'\(([\d.]+)-([\d.]+) fps\)', output)
        if match:
            min_fps = float(match.group(1))
            max_fps = float(match.group(2))

            frame_rates = [
                int(fps)
                for fps in range(int(max_fps), int(min_fps) - 1, -1)
                if int(fps) % 10 == 0
            ]

    elif "Discrete" in output:
        match = re.search(r'\(([\d.]+) fps\)', output)
        if match:
            frame_rates = [int(float(match.group(1)))]

    return frame_rates
