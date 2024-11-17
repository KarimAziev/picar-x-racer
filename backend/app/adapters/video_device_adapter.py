from typing import List, Optional

import cv2
from app.util.device import CameraInfo, list_camera_devices, try_video_path
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta


class VideoDeviceAdapater(metaclass=SingletonMeta):
    """
    A singleton class responsible for managing video capturing devices.
    This class handles finding available camera devices and setting up
    video capture sessions. It maintains a list of available camera
    devices and a list of devices that have previously failed to initialize.

    Attributes:
        logger (Logger): An instance of the Logger to handle logging.
        video_device (Optional[CameraInfo]): The currently active camera device information.
        video_devices (List[CameraInfo]): A list of all possible camera devices.
        failed_camera_devices (List[str]): A list of camera devices that have experienced initialization failures.
    """

    def __init__(self):
        """
        Initializes the VideoDeviceAdapater instance. Sets up the logger,
        and initializes attributes for tracking video devices and failed attempts.
        """
        self.logger = Logger(name=__name__)
        self.video_device: Optional[CameraInfo] = None
        self.video_devices: List[CameraInfo] = []
        self.failed_camera_devices: List[str] = []

    def find_camera_device(self):
        """
        Finds an available and operational camera device among the listed devices.
        Attempts to open each device and returns the first successful one.

        Returns:
            Tuple[Optional[object], Optional[str], Optional[str]]:
            A tuple containing the video capture object, the device path, and its information.
            Returns (None, None, None) if no operational device is found.
        """
        self.video_devices = list_camera_devices()

        for device_path, device_info in self.video_devices:
            if device_path in self.failed_camera_devices:
                continue

            cap = try_video_path(device_path)
            if not cap:
                self.logger.warning(
                    f"Error trying camera {device_path} ({device_info or 'Unknown category'})"
                )
                self.failed_camera_devices.append(device_path)
            else:
                return (cap, device_path, device_info)
        return (None, None, None)

    def find_camera_device_by_path(self, path):
        """
        Finds an available and operational camera device among the listed devices.
        Attempts to open each device and returns the first successful one.

        Returns:
            Tuple[Optional[object], Optional[str], Optional[str]]:
            A tuple containing the video capture object, the device path, and its information.
            Returns (None, None, None) if no operational device is found.
        """
        self.video_devices = list_camera_devices()

        for device_path, device_info in self.video_devices:
            if device_path == path:
                cap = try_video_path(device_path)
                if not cap:
                    self.logger.warning(
                        f"Error trying camera {device_path} ({device_info or 'Unknown category'})"
                    )
                    self.failed_camera_devices.append(device_path)
                else:
                    return (cap, device_path, device_info)

        return (None, None, None)

    def update_device(self, device: str):
        self.logger.info(f"Update device {device}")
        self.video_devices = list_camera_devices()
        for device_path, device_info in self.video_devices:
            self.logger.info(f"searching for {device} is {device_path}")
            if device_path == device:
                self.video_device = (device_path, device_info)
                return (device, device_info)

    def setup_video_capture(self) -> cv2.VideoCapture | None:
        """
        Sets up and returns a video capture object associated with an available camera device.
        If a device is already set up successfully, it attempts to reuse it.

        Returns:
            Optional[object]: The video capture object if successful, otherwise None.
            If the current device fails to reopen, it recursively tries to set up a capture with another available device.
        """
        if not self.video_device:
            cap, device, category = self.find_camera_device()
            if cap and device:
                self.video_device = (device, category or "")
                self.logger.info(
                    f"Started camera {device} ({category or 'Unknown category'})"
                )
                return cap

        device, category = self.video_device if self.video_device else (None, None)
        cap = try_video_path(device) if device else None
        if cap:
            self.logger.info(f"Started camera {device} {category}")
            return cap
        elif not cap and not device:
            self.logger.error(f"Failed to find camera")
            self.video_device = None
        elif not cap and device and not device in self.failed_camera_devices:
            self.logger.warning(
                f"Failed to reopen camera {device} ({category or 'Unknown category'}), trying other devices"
            )
            self.failed_camera_devices.append(device)
            self.video_device = None
            return self.setup_video_capture()
        else:
            return None
