import asyncio
import threading
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Union

import cv2
import numpy as np
from app.config.detectors import detectors
from app.config.video_enhancers import frame_enhancers
from app.controllers.video_device_controller import VideoDeviceController
from app.util.logger import Logger
from app.util.photo import height_to_width
from app.util.singleton_meta import SingletonMeta
from app.util.video_utils import encode_and_detect
from cv2 import VideoCapture
from websockets.server import WebSocketServerProtocol

# Constants for target width and height of video streams
TARGET_WIDTH = 320
TARGET_HEIGHT = 240


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
        self.video_device_manager = VideoDeviceController()
        self.executor_shutdown = False
        self.active_clients = 0
        self.target_fps = target_fps
        self.camera_run = False
        self.img: Optional[np.ndarray] = None
        self.stream_img: Optional[np.ndarray] = None
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
        stream_img = self.stream_img

        if stream_img is not None:
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
                stream_img,
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
            self.logger.info(
                f"generate_video_stream: Active Clients: {self.active_clients}"
            )
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

        self.logger.info(
            f"Starting camera loop with camera index {self.video_device_manager.camera_index}"
        )
        self.cap = self.video_device_manager.setup_video_capture(
            fps=self.target_fps, width=self.frame_width, height=self.frame_height
        )

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
                        self.video_device_manager.failed_camera_indexes.append(
                            self.video_device_manager.camera_index
                        )
                        self.cap.release()
                        new_index, _, device_info = (
                            self.video_device_manager.find_camera_index()
                        )
                        if isinstance(new_index, int):
                            self.logger.info(
                                f"Camera index {self.video_device_manager.camera_index} is failed, trying {new_index}: {device_info}"
                            )
                            self.video_device_manager.camera_index = new_index
                            self.cap = self.video_device_manager.setup_video_capture(
                                fps=self.target_fps,
                                width=self.frame_width,
                                height=self.frame_height,
                            )
                            failed_counter = 0
                            continue
                else:
                    failed_counter = 0
                self.frame_counter += 1

                self.img = frame
                self.stream_img = frame.copy()

        except Exception as e:
            self.logger.error(f"Exception occurred in camera loop: {e}")
        finally:
            self.cap.release()
            self.cap = None
            self.stream_img = None

            self.logger.info("Camera loop terminated and camera released.")

    def camera_start(
        self,
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
        self.logger.info(f"Starting camera with  fps={fps}")
        if self.camera_run:
            try:
                self.camera_close()
            except Exception as e:
                self.logger.error(f"Camera close error {e}")

        if fps:
            self.target_fps = fps

        self.frame_height = height
        self.frame_width = (
            width
            or height_to_width(
                height=height, target_width=TARGET_WIDTH, target_height=TARGET_HEIGHT
            )
            if height
            else None
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
        self.stream_img = None

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
        await self.start_camera_and_wait_for_stream_img()
        if self.executor_shutdown:
            self.recreate_executor()

    def recreate_executor(self):
        """
        Recreate the ProcessPoolExecutor if it has been shut down.
        """
        if self.executor_shutdown:
            self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
            self.executor_shutdown = False

    async def start_camera_and_wait_for_stream_img(
        self,
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
            self.camera_start(fps, width, height)

        counter = 0

        while True:
            if self.stream_img is not None:
                break
            if counter <= 1:
                self.logger.debug("waiting for flask img")
            counter += 1
            await asyncio.sleep(0.1)
