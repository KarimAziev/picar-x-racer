import os
import re
from typing import List, Optional, Tuple

import cv2
import pyudev
from app.util.device import (
    find_video_device,
    find_video_device_index,
    get_video_device_info,
)
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta

# This represents (index, device_path, device_info)
CameraInfo = Tuple[int, str, Optional[str]]


class VideoDeviceAdapater(metaclass=SingletonMeta):
    """
    Singleton adapter to manage video devices.

    Attributes:
    -----------
    camera_index : Optional[int]
        The index of the camera to be used. Defaults to 0.
    video_devices : List[str]
        List of available video devices.
    failed_camera_indexes : List[int]
        List of camera indexes that have failed to be opened.

    Methods:
    --------
    __init__(camera_index: Optional[int] = 0)
        Initializes the VideoDeviceAdapater instance.

    find_camera_index()
        Finds an available camera index. Prefers non-greyscale cameras.

    setup_video_capture(fps: int, width: Optional[int] = None, height: Optional[int] = None)
        Sets up the video capture device with specified FPS, width, and height.
    """

    def __init__(self, camera_index: Optional[int] = 0):
        self.logger = Logger(name=__name__)
        self.device = find_video_device()
        self.camera_index: int = (
            camera_index
            if isinstance(camera_index, int)
            else find_video_device_index() or 0
        )
        self.video_devices: List[CameraInfo] = []
        self.failed_camera_indexes: List[int] = []

    def discover_video_devices(self) -> List[str]:
        """
        Discover video devices on the system by using pyudev and fallback to manually checking /dev.

        Returns:
        --------
        List[str]: A list of available /dev/videoX device paths.
        """
        context = pyudev.Context()

        video_devices = []
        for device in context.list_devices(subsystem="video4linux"):
            try:
                parent_usb_vendor = device.properties.get("ID_VENDOR_ID")
                video_device_path = os.path.join("/dev", device.sys_name)

                if parent_usb_vendor:
                    video_devices.append(video_device_path)
                    self.logger.info(
                        f"Discovered external USB camera: {video_device_path}"
                    )

            except KeyError:
                pass
        if not video_devices:
            self.logger.warning(
                "No external USB cameras found. Scanning all /dev/video* devices."
            )
            video_devices = sorted(
                [
                    f"/dev/{dev}"
                    for dev in os.listdir("/dev")
                    if re.match(r"video[0-9]+", dev)
                ]
            )

        return video_devices

    def find_camera_index(self) -> Optional[CameraInfo]:
        """
        Finds an available camera index by scanning devices for cameras that can be successfully opened.

        This version prioritizes external USB cameras first. It falls back to other available non-greyscale or functional cameras.

        Returns:
        --------
        Optional[CameraInfo]
            A tuple containing the camera index (int), device path, and the device information (or None if none is found).
        """

        self.video_devices: List[CameraInfo] = [
            (i, path, get_video_device_info(path))
            for i, path in enumerate(self.discover_video_devices())
        ]

        greyscale_cameras: List[CameraInfo] = []

        for index, device_path, device_info in self.video_devices:
            if index in self.failed_camera_indexes:
                continue

            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                ret, frame = cap.read()

                if ret and frame is not None:
                    if device_info and "8-bit Greyscale" in device_info:
                        greyscale_cameras.append((index, device_path, device_info))
                    else:
                        self.logger.info(
                            f"Using camera: {device_path}, info: {device_info}"
                        )
                        cap.release()
                        return (index, device_path, device_info)
                else:

                    self.failed_camera_indexes.append(index)
                    self.logger.warning(
                        f"Failed to get valid frame from camera {device_path}."
                    )

            cap.release()

        if greyscale_cameras:
            return greyscale_cameras[0]

    def setup_video_capture(
        self, fps: int, width: Optional[int] = None, height: Optional[int] = None
    ) -> cv2.VideoCapture:
        """
        Sets up the video capture device with specified FPS, width, and height.

        Parameters:
        -----------
        fps : int
            Frames per second for the video capture.
        width : Optional[int], optional
            Width of the video frame. Defaults to None.
        height : Optional[int], optional
            Height of the video frame. Defaults to None.

        Returns:
        --------
        cv2.VideoCapture
            The video capture object.

        Raises:
        -------
        SystemExit
            If the video capture device cannot be opened.
        """
        cap = cv2.VideoCapture(self.camera_index)
        if not cap or not cap.isOpened():
            if cap:
                try:
                    cap.release()
                except Exception as err:
                    self.logger.log_exception("Couln't release the cap", err)

            self.logger.error(f"Failed to open camera at {self.camera_index}.")
            self.failed_camera_indexes.append(self.camera_index)
            info = self.find_camera_index()
            new_index, _, device_info = info if info is not None else (None, None, None)
            if isinstance(new_index, int):
                self.logger.error(
                    f"Failed to open camera at {self.camera_index}, trying {new_index}: {device_info}"
                )
                self.camera_index = new_index
                return self.setup_video_capture(fps=fps, width=width, height=height)
            else:
                self.logger.error(f"Failed to open camera at {self.camera_index}.")
                raise SystemExit(
                    f"Exiting: Camera {self.camera_index} couldn't be opened."
                )

        if width and height:
            self.logger.info(f"Frame_width: {width}, frame_height: {height}")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

        self.logger.info(f"FPS: {fps}")

        cap.set(cv2.CAP_PROP_FPS, fps)
        return cap

    def find_and_setup_alternative_camera(
        self, fps: int, width: Optional[int] = None, height: Optional[int] = None
    ):
        """
        Attempts to find and set up an alternative video capture device if the current one fails.

        This method tries to find an alternative video capture device by checking
        other available video devices when the current device fails to open or operate correctly.
        It then sets up the video capture with the specified FPS, width, and height.

        Parameters:
        -----------
        fps : int
            Frames per second for the video capture.
        width : Optional[int], optional
            Width of the video frame. Defaults to None.
        height : Optional[int], optional
            Height of the video frame. Defaults to None.

        Returns:
        --------
        cv2.VideoCapture
            The video capture object for the newly found camera.

        Raises:
        -------
        SystemExit
            If no alternative video capture device can be successfully set up.
        """
        if isinstance(self.camera_index, int):
            self.failed_camera_indexes.append(self.camera_index)

        info = self.find_camera_index()

        if info is None:
            self.logger.warning(f"Failed to find alternative camera device")
            return None

        new_index, _, device_info = info
        if isinstance(new_index, int):
            self.logger.info(
                f"Camera index {self.camera_index} is failed, trying {new_index}:\n{device_info}"
            )
            self.camera_index = new_index
            return self.setup_video_capture(
                fps=fps,
                width=width,
                height=height,
            )
