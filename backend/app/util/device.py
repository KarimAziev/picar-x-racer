import os
import re
import subprocess
from typing import List

import cv2
import pyudev
import usb.core
import usb.util
from app.util.logger import Logger

logger = Logger(__name__)


def get_video_device_info(device_path: str) -> str:
    """
    Get detailed information of the video device using `v4l2-ctl` command.

    Args:
        device_path (str): Path to the video device.

    Returns:
        str: Detailed information about the video device.
    """
    try:
        result = subprocess.run(
            ["v4l2-ctl", "--device", device_path, "--all"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.stdout
    except Exception as e:
        return f"Error checking device {device_path}: {e}"


def try_video_path(path: str):
    result = None
    cap = cv2.VideoCapture(path)

    try:
        ret, _ = cap.read()
        result = path if ret else None
    except Exception as err:
        logger.warning(f"Error while trying camera at path {path} {err}")
    finally:
        if cap.isOpened():
            cap.release()

    return result


def display_best_device_info():
    """
    Attempts to display information for the preferred camera device, based on the priority:
    - External USB camera
    - Camera Module/Onboard camera
    - Built-in camera (as fallback)
    """
    camera_device_path = find_video_device()

    if camera_device_path:
        info = get_video_device_info(camera_device_path)
        logger.info(f"Video Device Information {camera_device_path}:\n{info}")
    else:
        logger.info("No video device found.")


def is_usb_device_connected(vendor_id: int, product_id: int) -> bool:
    """
    Checks if a USB device with a specific vendor ID and product ID is connected.

    This function leverages the `pyusb` library to scan for USB devices and check whether there
    is a device matching the provided vendor ID and product ID.

    Args:
        vendor_id (int): The vendor ID of the USB device.
        product_id (int): The product ID of the USB device.

    Returns:
        bool: True if a device matching the vendor ID and product ID is found; False otherwise.
    """
    try:
        device = usb.core.find(idVendor=vendor_id, idProduct=product_id)
        return device is not None

    except Exception as e:
        logger.log_exception(
            f"Error searching USB device with Vendor ID {vendor_id} and Product ID {product_id}: ",
            e,
        )
        return False


def get_available_cameras():
    """
    Finds a video device by preferring an externally connected USB camera, a camera module,
    or a built-in camera as a fallback.

    The function scans for video devices connected via USB first. If no external USB camera
    is found, it checks for any other available video devices.

    Returns:
        str: The path to the preferred video device (`/dev/videoX`) or an empty string if none are found.
    """
    try:
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.stdout
    except Exception as e:
        return f"Error checking device {e}"


def get_available_devices(exclude_devices: List[str] = []) -> List[str]:
    context = pyudev.Context()

    video_devices = context.list_devices(subsystem="video4linux")
    by_vendors = {}
    non_vendors: List[str] = []

    for device in video_devices:
        video_device_path = os.path.join("/dev", device.sys_name)
        parent_usb_vendor = None
        if video_device_path in exclude_devices:
            continue

        working = try_video_path(video_device_path)
        if working:
            try:
                parent_usb_vendor = device.properties.get("ID_VENDOR_ID")

                logger.debug(
                    f"Device {device.sys_name} parent {device.parent} parent_usb_vendor: {parent_usb_vendor}"
                )
            except KeyError:
                pass

            if isinstance(parent_usb_vendor, str):
                if not by_vendors.get(parent_usb_vendor):
                    by_vendors[parent_usb_vendor] = [video_device_path]
                else:
                    by_vendors[parent_usb_vendor].append(video_device_path)
            else:
                non_vendors.append(video_device_path)

    return [item for sublist in by_vendors.values() for item in sublist] + non_vendors


def find_video_device(exclude_devices: List[str] = []):
    context = pyudev.Context()

    video_devices = context.list_devices(subsystem="video4linux")
    primary_cands: List[str] = []
    not_primary_cands: List[str] = []
    by_vendors = {}

    for device in video_devices:
        video_device_path = os.path.join("/dev", device.sys_name)
        parent_usb_vendor = None
        if video_device_path in exclude_devices:
            continue

        try:
            parent_usb_vendor = device.properties.get("ID_VENDOR_ID")

            logger.debug(
                f"Device {device.sys_name} parent {device.parent} parent_usb_vendor: {parent_usb_vendor}"
            )
        except KeyError:
            pass

        if isinstance(parent_usb_vendor, str):
            if not by_vendors.get(parent_usb_vendor):
                by_vendors[parent_usb_vendor] = True
                primary_cands.append(video_device_path)
            else:
                not_primary_cands.append(video_device_path)
        else:
            not_primary_cands.append(video_device_path)

    for item in primary_cands + not_primary_cands:
        if try_video_path(item):
            return item


def find_video_device_index():
    device_name = find_video_device()

    match = re.search(r"/[^\d]*(\d+)$", device_name) if device_name else None
    if match:
        return int(match.group(1))
    return None
