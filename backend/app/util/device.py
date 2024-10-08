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
        cap = cv2.VideoCapture(path, cv2.CAP_V4L2)
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


COMMON_SIZES = [
    (640, 480),  # VGA
    (800, 600),  # SVGA
    (1024, 768),  # XGA
]


def parse_v4l2_formats(device: str, category: str) -> List[Dict[str, str]]:
    """
    Parse the output of v4l2-ctl --list-formats-ext for the specified device.

    Args:
        device (str): The path to the camera device, e.g., '/dev/video0'.
        category (str): The camera type or category for labeling purposes.

    Returns:
        List[Dict[str, str]]: A formatted list of dictionaries where each dict contains a
                              'value' and 'label' representing format, resolution, and FPS.
    """
    try:
        cmd = ["v4l2-ctl", "--list-formats-ext", "--device", device]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing v4l2-ctl: {e}")
        return []

    logger.debug(f"Raw output:\n{output}")

    return parse_v4l2_formats_output(output, device, category)


def parse_v4l2_formats_output(
    output: str, device: str, category: str
) -> List[Dict[str, str]]:
    """
    Parse the output of v4l2-ctl --list-formats-ext for the specified device.

    Args:
        device (str): The path to the camera device, e.g., '/dev/video0'.
        category (str): The camera type or category for labeling purposes.

    Returns:
        List[Dict[str, str]]: A formatted list of dictionaries where each dict contains a
                              'value' and 'label' representing format, resolution, and FPS.
    """
    formats = []

    format_pattern = re.compile(r"\[\d+\]: '([A-Z0-9]+)' \((.+)\)")
    resolution_discrete_pattern = re.compile(r"Size: Discrete (\d+x\d+)")
    resolution_stepwise_pattern = re.compile(
        r"Size: Stepwise (\d+x\d+) - (\d+x\d+) with step (\d+)/(\d+)"
    )
    fps_pattern = re.compile(r"Interval: Discrete ([0-9.]+)s \((\d+)\.000 fps\)")

    current_format = None
    current_description = None
    frame_size = None

    for line in output.splitlines():
        line = line.strip()
        logger.debug(f"Parsing line: {line}")

        format_match = format_pattern.match(line)
        if format_match:
            current_format = format_match.group(1)
            current_description = format_match.group(2)
            logger.debug(
                f"Found format: {current_format}, Description: {current_description}"
            )

        resolution_discrete_match = resolution_discrete_pattern.search(line)
        if resolution_discrete_match:
            frame_size = resolution_discrete_match.group(1)
            logger.debug(f"Found discrete resolution: {frame_size}")

        resolution_stepwise_match = resolution_stepwise_pattern.search(line)
        if resolution_stepwise_match:
            min_size = resolution_stepwise_match.group(1)
            max_size = resolution_stepwise_match.group(2)
            step_x = resolution_stepwise_match.group(3)
            step_y = resolution_stepwise_match.group(4)
            logger.debug(
                f"Found stepwise resolution: {min_size} to {max_size} with steps {step_x}/{step_y}"
            )

            for width, height in COMMON_SIZES:
                frame_size = f"{width}x{height}"

                fps_value = "30"
                value = f"{device}:{current_format}:{frame_size}:{fps_value}"
                label = f"{device} ({category}) {current_format} ({current_description}), {frame_size} @ {fps_value} fps"
                formats.append(
                    {
                        "value": value,
                        "label": label,
                        "device": device,
                        "size": frame_size,
                        "fps": fps_value,
                        "pixel_format": current_format,
                    }
                )
                logger.debug(f"Added format: {value}, label: {label}")

        fps_match = fps_pattern.search(line)
        if fps_match:
            fps_value = fps_match.group(2)
            logger.debug(f"Found FPS: {fps_value}")

            if current_format and frame_size:
                value = f"{device}:{current_format}:{frame_size}:{fps_value}"
                label = f"{device} ({category}) {current_format} ({current_description}), {frame_size} @ {fps_value} fps"
                formats.append(
                    {
                        "value": value,
                        "label": label,
                        "device": device,
                        "size": frame_size,
                        "fps": fps_value,
                        "pixel_format": current_format,
                    }
                )
                logger.debug(f"Added format: {value}, label: {label}")

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
