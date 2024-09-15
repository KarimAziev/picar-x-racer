import os
from typing import List, Optional, Tuple

import cv2
from app.util.device import get_video_device_info
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta

CameraInfo = Tuple[int, str, Optional[str]]


class VideoDeviceController(metaclass=SingletonMeta):
    """
    Singleton controller to manage video devices.

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
        Initializes the VideoDeviceController instance.

    find_camera_index()
        Finds an available camera index. Prefers non-greyscale cameras.

    setup_video_capture(fps: int, width: Optional[int] = None, height: Optional[int] = None)
        Sets up the video capture device with specified FPS, width, and height.
    """

    def __init__(self, camera_index: Optional[int] = 0):
        self.logger = Logger(name=__name__)
        self.camera_index = camera_index if camera_index else 0
        self.video_devices: List[str] = []
        self.failed_camera_indexes: List[int] = []

    def find_camera_index(self):
        """
        Finds an available camera index. Prefers non-greyscale cameras.

        Returns:
        --------
        CameraInfo
            A tuple containing the camera index, device path, and device information.
        """

        greyscale_cameras: List[CameraInfo] = []

        self.video_devices = self.video_devices or [
            f for f in os.listdir("/dev") if f.startswith("video")
        ]
        for device in self.video_devices:
            device_path = os.path.join("/dev", device)
            index = int(device.replace("video", ""))
            if index not in self.failed_camera_indexes:
                cap = cv2.VideoCapture(index)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is None:
                        self.failed_camera_indexes.append(index)
                        self.video_devices.remove(device)
                    else:
                        device_info = get_video_device_info(device_path)
                        if device_info and "8-bit Greyscale" in device_info:
                            greyscale_cameras.append((index, device_path, device_info))
                        else:
                            cap.release()
                            return (index, device_path, device_info)
                    cap.release()

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
        if not cap.isOpened():
            cap.release()
            self.logger.error(f"Failed to open camera at {self.camera_index}.")
            self.failed_camera_indexes.append(self.camera_index)
            new_index, _, device_info = self.find_camera_index()
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

        new_index, _, device_info = self.find_camera_index()
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
