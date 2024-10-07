import os
import re
import subprocess
from typing import Dict, List, Optional, Tuple, Union

import cv2
from app.util.logger import Logger

logger = Logger(__name__)


CameraInfo = Tuple[str, str]


def try_video_path(path: str | int):
    """
    Tries to open a video capture at a specified path.

    Attempts to create and read from a video capture object using OpenCV.
    If successful, returns the video capture object; otherwise, returns None.

    Parameters:
        path (str): The file path or device path to the video stream.

    Returns:
        Optional[cv2.VideoCapture]: The video capture object if the path is valid and readable, otherwise None.
    """
    result: Optional[bool] = None
    cap = None

    try:
        cap = cv2.VideoCapture(path)
        result, _ = cap.read()
    except Exception as err:
        logger.log_exception("Camera Error:", err)
        if cap and cap.isOpened():
            cap.release()

    return cap if result else None


def v4l2_list_devices() -> list[str]:
    """
    Lists V4L2 video capture devices on the system.

    Uses the `v4l2-ctl` command-line utility to get details about available
    video capture devices on the system and returns the raw output lines.

    Returns:
        list[str]: A list of output lines from the `v4l2-ctl --list-devices` command. Each line may contain information about a device or its category.
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

    except Exception as e:
        logger.log_exception("List devices failed", e)

    return lines


def list_camera_devices() -> List[CameraInfo]:
    """
    Retrieves a list of available camera devices.

    Parses the output from `v4l2_list_devices` to extract camera paths and their respective categories.
    Returns the primary camera for each category first, followed by secondary cameras. If no cameras are found,
    falls back to listing potential camera devices based on video files in /dev/.

    Returns:
        List[CameraInfo]: A list of tuples, each containing a device path and a category, representing available cameras.
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

    primary_cameras.reverse()

    result = primary_cameras + secondary_cameras
    if len(result) >= 1:
        return result

    dev_video_files = sorted(
        [f"/dev/{dev}" for dev in os.listdir("/dev") if re.match(r"video[0-9]+", dev)]
    )
    return [(device, "") for device in dev_video_files]


def list_available_camera_devices():
    result: List[Dict[str, Union[str, List[Dict[str, str]]]]] = []
    for key, category in list_camera_devices():
        formats = parse_v4l2_formats(key, category)
        if formats:
            item = {
                "value": key,
                "label": f"{key} ({category or 'Unknown'})",
                "formats": formats,
            }
            result.append(item)

    return result


def parse_v4l2_formats(device: str, category: str) -> List[Dict[str, str]]:
    """
    Parse the output of v4l2-ctl --list-formats-ext for the specified device.

    Args:
        device (str): The path to the camera device, e.g., '/dev/video0'.

    Returns:
        List[Dict[str, str]]: A formatted list of dictionaries where each dict contains a
                              'value' and 'label' representing format, resolution, and FPS.
    """
    try:
        # Run the v4l2-ctl command to list formats with detailed information
        cmd = ["v4l2-ctl", "--list-formats-ext", "--device", device]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing v4l2-ctl: {e}")
        return []

    logger.info(f"Raw output:\n{output}")

    formats = []

    # Regex patterns to capture the format type, resolution, and FPS values.
    format_pattern = re.compile(r"\[\d+\]: '([A-Z0-9]+)' \((.+)\)")
    resolution_pattern = re.compile(r"Size: Discrete (\d+x\d+)")
    fps_pattern = re.compile(r"Interval: Discrete ([0-9.]+)s \((\d+)\.000 fps\)")

    current_format = None
    current_description = None
    frame_size = None

    # Parse the output line by line
    for line in output.splitlines():

        line = line.strip()

        # Match format type: e.g., [0]: 'MJPG' (Motion-JPEG, compressed)
        format_match = format_pattern.match(line)
        if format_match:
            current_format = format_match.group(1)
            current_description = format_match.group(2)

        # Match resolution: e.g., Size: Discrete 1920x1080
        resolution_match = resolution_pattern.search(line)
        if resolution_match:
            frame_size = resolution_match.group(1)

        # Match FPS: e.g., Interval: Discrete 0.033s (30.000 fps)
        fps_match = fps_pattern.search(line)
        if fps_match:
            fps_value = fps_match.group(2)

            # Build the value and label for this format and resolution
            if current_format and frame_size:
                value = f"{device}:{current_format}:{frame_size}:{fps_value}"
                label = f"{device} ({category}) {current_format} ({current_description}), {frame_size} @ {fps_value} fps"
                formats.append({"value": value, "label": label})

    return formats
