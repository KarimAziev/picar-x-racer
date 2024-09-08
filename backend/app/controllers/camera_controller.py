import asyncio
import os
import subprocess
import threading
from concurrent.futures import ProcessPoolExecutor
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from app.util.video_utils import (
    detect_full_body_faces,
    detect_human_faces,
    encode_and_detect,
    simulate_robocop_vision,
    detect_cat_extended_faces,
    detect_cat_faces,
)
from app.util.mobile_net import (
    detect_objects_with_mobilenet,
)
from cv2 import VideoCapture
from websockets.server import WebSocketServerProtocol

# Constants for target width and height of video streams
TARGET_WIDTH = 320
TARGET_HEIGHT = 240

CameraInfo = Tuple[int, str, Optional[str]]

frame_enhancers = {"robocop_vision": simulate_robocop_vision}

detectors = {
    "mobile_net": detect_objects_with_mobilenet,
    "cat": detect_cat_faces,
    "cat_extended": detect_cat_extended_faces,
    "human_body": detect_full_body_faces,
    "human_face": detect_human_faces,
}


class CameraController(metaclass=SingletonMeta):
    """
    CameraController is a singleton class responsible for managing camera operations, including
    starting the camera, capturing frames, flipping frames, encoding frames into different formats,
    and streaming video frames to clients.
    """

    def __init__(self, max_workers=None, target_fps=30):
        self.max_workers = max_workers
        self.logger = Logger(name=__name__)
        self.executor = ProcessPoolExecutor(max_workers=max_workers)
        self.executor_shutdown = False
        self.active_clients = 0
        self.target_fps = target_fps
        self.camera_index = 0
        self.camera_vflip = False
        self.camera_hflip = False
        self.camera_run = False
        self.img: Optional[np.ndarray] = None
        self.flask_img: Optional[np.ndarray] = None
        self.video_devices: List[str] = []
        self.failed_camera_indexes: List[int] = []
        self.cap: Union[VideoCapture, None] = None
        self.frame_skip_interval = 2
        self.frame_counter = 0
        self.frame_width: Optional[int] = None
        self.frame_height: Optional[int] = None
        self.video_feed_detect_mode: Optional[str] = None
        self.video_feed_enhance_mode: Optional[str] = None
        self.video_feed_quality = 100
        self.video_feed_format = ".jpg"
        self.inhibit_detection: bool = False

    def generate_frame(self):
        img_copy = self.flask_img.copy() if self.flask_img is not None else None

        if img_copy is not None:
            format = self.video_feed_format
            video_feed_enhance_mode = self.video_feed_enhance_mode
            video_feed_detect_mode = self.video_feed_detect_mode
            inhibit_detection = self.inhibit_detection
            video_feed_quality = self.video_feed_quality
            frame_enhancer = (
                frame_enhancers.get(video_feed_enhance_mode)
                if video_feed_enhance_mode
                else None
            )
            detection_func = (
                detectors.get(video_feed_detect_mode)
                if video_feed_detect_mode and not inhibit_detection
                else None
            )

            encode_params = (
                [cv2.IMWRITE_JPEG_QUALITY, video_feed_quality]
                if format == ".jpg"
                else []
            )
            encoded_frame = encode_and_detect(
                img_copy,
                format,
                encode_params,
                frame_enhancer,
                detection_func,
            )

            return encoded_frame

    async def generate_video_stream_for_websocket(
        self, websocket: WebSocketServerProtocol
    ):
        await self.restart()
        self.active_clients += 1
        self.logger.info(f"Active websocket clients: {self.active_clients}")
        skip_count = 0
        try:
            while True:
                encoded_frame = self.generate_frame()
                if encoded_frame:
                    await websocket.send(encoded_frame)
                else:
                    if skip_count < 1:
                        self.logger.debug("Flask image is None, skipping frame.")
                        skip_count += 1
                await asyncio.sleep(0)
        finally:
            self.active_clients -= 1
            self.logger.info(f"generate_video_stream: Active Clients: {self.active_clients}")
            # if self.active_clients == 0 and not self.executor_shutdown:
                # self.executor.shutdown(wait=True, cancel_futures=True)
                # self.executor_shutdown = True
                # self.logger.info("Executor shut down due to no active clients.")
                # self.camera_close()  # Close the camera when no active clients

    def generate_video_stream(
        self,
    ):
        self.active_clients += 1
        self.logger.info(f"generate_video_stream: Active Clients: {self.active_clients}")
        skip_count = 0
        try:
            while True:
                encoded_frame = self.generate_frame()
                if encoded_frame:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded_frame + b"\r\n"
                else:
                    if skip_count < 1:
                        self.logger.debug("Flask image is None, skipping frame.")
                        skip_count += 1
        finally:
            self.active_clients -= 1
            self.logger.info(f"generate_video_stream: Active Clients: {self.active_clients}")
            if self.active_clients == 0 and not self.executor_shutdown:
                self.executor.shutdown(wait=True, cancel_futures=True)
                self.executor_shutdown = True
                self.logger.info("Executor shut down due to no active clients.")
                self.camera_close()  # Close the camera when no active clients

    def camera_thread_func(self):
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception as e:
            self.logger.error(f"Exception occurred in camera loop: {e}")
        finally:
            self.cap = None

        self.logger.info(f"Starting camera loop with camera index {self.camera_index}")
        self.cap = self.camera_thread_func_setup()

        failed_counter = 0
        max_failed_attempt_count = 10

        try:
            while self.camera_run:
                ret, frame = self.cap.read()
                if not ret:
                    if failed_counter < max_failed_attempt_count:
                        failed_counter += 1
                        self.logger.error("Failed to read frame from camera.")
                        continue
                    else:
                        self.failed_camera_indexes.append(self.camera_index)
                        self.cap.release()
                        new_index, _, device_info = self.find_camera_index()
                        if isinstance(new_index, int):
                            self.logger.info(
                                f"Camera index {self.camera_index} is failed, trying {new_index}: {device_info}"
                            )
                            self.camera_index = new_index
                            self.cap = self.camera_thread_func_setup()
                            failed_counter = 0
                            continue
                else:
                    failed_counter = 0

                if self.frame_counter % self.frame_skip_interval == 0:
                    if self.camera_vflip:
                        frame = cv2.flip(frame, 0)
                    if self.camera_hflip:
                        frame = cv2.flip(frame, 1)

                self.frame_counter += 1

                self.img = frame
                self.flask_img = frame.copy()

        except Exception as e:
            self.logger.error(f"Exception occurred in camera loop: {e}")
        finally:
            self.cap.release()
            self.cap = None
            self.flask_img = None

            self.logger.info("Camera loop terminated and camera released.")

    @staticmethod
    def height_to_width(height: int):
        aspect_ratio = TARGET_WIDTH / TARGET_HEIGHT
        width = aspect_ratio * height
        return int(width)

    @staticmethod
    def get_device_info(device_path: str) -> str:
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

    def find_camera_index(self):
        """
        Find an available camera index by iterating over video devices and checking their availability.

        Returns:
            CameraInfo: Tuple containing index, device path, and device information of the selected camera.
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
                        device_info = CameraController.get_device_info(device_path)
                        if device_info and "8-bit Greyscale" in device_info:
                            greyscale_cameras.append((index, device_path, device_info))
                        else:
                            cap.release()
                            return (index, device_path, device_info)
                    cap.release()

        return greyscale_cameras[0]

    def camera_thread_func_setup(self):
        """
        Set up the camera for capturing frames by configuring width, height, and FPS.

        Returns:
            cv2.VideoCapture: Opened video capture object.
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
                return self.camera_thread_func_setup()
            else:
                self.logger.error(f"Failed to open camera at {self.camera_index}.")
                raise SystemExit(
                    f"Exiting: Camera {self.camera_index} couldn't be opened."
                )

        if self.frame_width and self.frame_height:
            self.logger.info(
                f"Frame_width: {self.frame_width}, frame_height: {self.frame_height}"
            )
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

        self.logger.info(f"FPS: {self.target_fps}")

        cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        return cap

    def camera_start(
        self,
        vflip=False,
        hflip=False,
        fps: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ):
        """
        Start the camera capturing loop in a separate thread.

        Args:
            vflip (bool): Flag to determine vertical flip of the camera frame.
            hflip (bool): Flag to determine horizontal flip of the camera frame.
            fps (int): Frames per second for the camera.
        """
        self.logger.info(
            f"Starting camera with vflip={vflip}, hflip={hflip}, fps={fps}"
        )
        if self.camera_run:
            try:
                self.camera_close()
            except Exception as e:
                self.logger.error(f"Camera close error {e}")

        self.camera_hflip = hflip
        self.camera_vflip = vflip
        if fps:
            self.target_fps = fps

        self.frame_height = height
        self.frame_width = (
            width or CameraController.height_to_width(height) if height else None
        )
        self.camera_run = True

        self.camera_thread = threading.Thread(target=self.camera_thread_func)
        self.camera_thread.start()

    def camera_close(self):
        """
        Close the camera and clean up resources.
        """
        self.logger.info("Closing camera")
        self.camera_run = False
        if hasattr(self, "camera_thread"):
            self.camera_thread.join()
        self.flask_img = None

    def shutdown(self):
        """
        Close the camera and clean up resources.
        """
        self.logger.info("Closing camera")
        self.camera_close()

        if not self.executor_shutdown:
            self.executor.shutdown(wait=True)
            self.executor_shutdown = True

    async def restart(self):
        await self.start_camera_and_wait_for_flask_img()
        if self.executor_shutdown:
            self.recreate_executor()

    def recreate_executor(self):
        """
        Recreate the ThreadPoolExecutor if it has been shut down.
        """
        if self.executor_shutdown:
            self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
            self.executor_shutdown = False

    async def start_camera_and_wait_for_flask_img(
        self,
        vflip=False,
        hflip=False,
        fps: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ):
        """
        Asynchronously start the camera and wait for the Flask image to be available.

        Args:
            vflip (bool): Flag to determine vertical flip of the camera frame.
            hflip (bool): Flag to determine horizontal flip of the camera frame.
            fps (int): Frames per second for the camera.
        """
        if not self.camera_run:
            self.camera_start(vflip, hflip, fps, width, height)

        counter = 0

        while True:
            if self.flask_img is not None:
                break
            if counter <= 1:
                self.logger.debug("waiting for flask img")
            counter += 1
            await asyncio.sleep(0.1)

    async def take_photo(self, photo_name: str, path: str) -> bool:
        """
        Asynchronously take a photo and save it to the specified path.

        Args:
            photo_name (str): Name of the photo file.
            path (str): Directory path to save the photo.

        Returns:
            bool: Status indicating success or failure of taking the photo.
        """
        self.logger.info(f"Taking photo '{photo_name}' at path {path}")
        if not os.path.exists(path):
            os.makedirs(name=path, mode=0o751, exist_ok=True)
            await asyncio.sleep(0.01)

        status = False
        for _ in range(5):
            img_copy = self.img.copy() if self.img is not None else None

            if img_copy is not None:
                status = cv2.imwrite(os.path.join(path, photo_name), img_copy)
                break
            else:
                await asyncio.sleep(0.01)
        else:
            status = False

        return status

    def convert_listproxy_to_array(self, listproxy_obj):
        """
        Convert a ListProxy object to a numpy array.

        Args:
            listproxy_obj: A ListProxy object to be converted.

        Returns:
            np.ndarray: Converted numpy array.

        Raises:
            ValueError: If the ListProxy object is None.
        """
        if listproxy_obj is None:
            self.logger.error("ListProxy object is None")
            raise ValueError("ListProxy object is None")
        np_array = np.array(listproxy_obj, dtype=np.uint8)
        return np_array
