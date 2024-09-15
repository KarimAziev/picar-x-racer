import asyncio
import multiprocessing as mp
import queue
import threading
from typing import Optional, Union

import cv2
import numpy as np
from app.config.video_enhancers import frame_enhancers
from app.controllers.video_device_controller import VideoDeviceController
from app.util.logger import Logger
from app.util.overlay_detecton import overlay_detection
from app.util.photo import height_to_width
from app.util.singleton_meta import SingletonMeta
from app.util.video_utils import encode
from cv2 import VideoCapture
from websockets.server import WebSocketServerProtocol

# Constants for target width and height of video streams
TARGET_WIDTH = 320
TARGET_HEIGHT = 240


class CameraController(metaclass=SingletonMeta):
    """
    The `CameraController` singleton class manages camera operations, video streaming,
    and object detection functionality. It handles starting and stopping the camera,
    capturing frames, streaming video to clients, and processing object detection in
    a separate process.

    Attributes:
        logger (Logger): Logger instance for logging messages.
        video_device_manager (VideoDeviceController): Manages video capture devices.
        active_clients (int): Number of active clients connected to the video stream.
        target_fps (int): Target frames per second for video capture.
        camera_run (bool): Flag indicating whether the camera is running.
        stream_img (Optional[np.ndarray]): Latest frame captured from the camera for streaming.
        frame_width (Optional[int]): Width of the video frames.
        frame_height (Optional[int]): Height of the video frames.
        video_feed_enhance_mode (Optional[str]): Current video enhancement mode.
        video_feed_quality (int): Quality parameter for video encoding (1-100).
        video_feed_format (str): Format for video encoding (e.g., '.jpg', '.png').
        _video_feed_detect_mode (Optional[str]): Current detection mode for object detection.
        inhibit_detection (bool): Flag to inhibit detection processing.
        frame_queue (multiprocessing.Queue): Queue for frames to be processed by the detection process.
        detection_queue (multiprocessing.Queue): Queue for detection results from the detection process.
        control_queue (multiprocessing.Queue): Queue for control messages to the detection process.
        last_detection_result (Optional[Dict]): Latest detection result received.
    """

    def __init__(self, target_fps=30):
        """
        Initializes the `CameraController` singleton instance.

        Args:
            target_fps (int, optional): Target frames per second for video capture.
                Defaults to 30.
        """
        self.logger = Logger(name=__name__)
        self.video_device_manager = VideoDeviceController()
        self.active_clients = 0
        self.target_fps = target_fps
        self.camera_run = False
        self.img: Optional[np.ndarray] = None
        self.stream_img: Optional[np.ndarray] = None
        self.cap: Union[VideoCapture, None] = None
        self.frame_counter = 0
        self.frame_width: Optional[int] = None
        self.frame_height: Optional[int] = None
        self.video_feed_enhance_mode: Optional[str] = None
        self.video_feed_quality = 100
        self.video_feed_format = ".jpg"
        self._video_feed_detect_mode: Optional[str] = None
        self.inhibit_detection: bool = False
        self.frame_queue = mp.Queue(maxsize=5)
        self.detection_queue = mp.Queue(maxsize=5)
        self.control_queue = mp.Queue()
        self.last_detection_result = None

    @property
    def video_feed_detect_mode(self):
        """
        Gets the current video feed detection mode.

        Returns:
            Optional[str]: The current detection mode (e.g., 'cat', 'person', 'all'),
            or None if detection is disabled.
        """

        return self._video_feed_detect_mode

    @video_feed_detect_mode.setter
    def video_feed_detect_mode(self, new_mode):
        """
        Sets the video feed detection mode and communicates the change to the detection process.

        Args:
            new_mode (Optional[str]): The new detection mode to set. If None, detection is disabled.
        """

        self.logger.info(f"Setting video_feed_detect_mode to {new_mode}")
        self._video_feed_detect_mode = new_mode
        if self.camera_run and hasattr(self, "control_queue"):
            command = {"command": "set_detect_mode", "mode": new_mode}
            self.control_queue.put(command)

    def generate_frame(self):
        """
        Generates a video frame for streaming.

        Retrieves the latest detection results, overlays detection annotations onto the frame,
        applies any video enhancements, encodes the frame in the specified format, and returns
        it as a byte array ready for streaming.

        Returns:
            Optional[bytes]: The encoded video frame as a byte array, or None if no frame is available.
        """
        while True:
            try:
                self.last_detection_result = self.detection_queue.get_nowait()
            except queue.Empty:
                break

        if self.stream_img is not None:
            format = self.video_feed_format
            video_feed_enhance_mode = self.video_feed_enhance_mode
            video_feed_quality = self.video_feed_quality
            frame = self.stream_img.copy()
            if self.last_detection_result is not None:
                frame = overlay_detection(frame, self.last_detection_result)
            frame_enhancer = (
                frame_enhancers.get(video_feed_enhance_mode)
                if video_feed_enhance_mode
                else None
            )

            encode_params = (
                [cv2.IMWRITE_JPEG_QUALITY, video_feed_quality]
                if format == ".jpg"
                else []
            )
            encoded_frame = encode(
                frame,
                format,
                encode_params,
                frame_enhancer,
            )

            return encoded_frame

    def start_camera(
        self,
        fps: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ):
        """
        Starts the camera capture thread and the detection process.

        Configures the camera settings, initializes queues, and starts the threads and processes
        necessary for capturing and processing video frames.

        Args:
            fps (Optional[int], optional): Target frames per second for video capture.
                If None, uses the existing `target_fps` value.
            width (Optional[int], optional): Desired width of the video frames.
                If None, calculates based on `height` and target aspect ratio.
            height (Optional[int], optional): Desired height of the video frames.
                If None, uses default or calculates based on `width`.
        """
        self.logger.info(f"Starting camera with  fps={fps}")
        if self.camera_run:
            try:
                self.stop_camera()
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
        # Start the camera capture in a thread
        self.capture_thread = threading.Thread(target=self.camera_thread_func)
        self.capture_thread.start()

        # Start the detection process
        self.detection_process = mp.Process(target=self.detection_process_func)
        self.detection_process.start()

        if self.video_feed_detect_mode:
            command = {
                "command": "set_detect_mode",
                "mode": self.video_feed_detect_mode,
            }
            self.control_queue.put(command)

    async def start_camera_and_wait_for_stream_img(
        self,
        fps: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ):
        """
        Asynchronously starts the camera and waits until the first frame is available.

        Useful for ensuring that the camera is ready and frames are available before
        starting operations that depend on the video stream.

        Args:
            fps (Optional[int], optional): Target frames per second for video capture.
                If None, uses the existing `target_fps` value.
            width (Optional[int], optional): Desired width of the video frames.
                If None, calculates based on `height` and target aspect ratio.
            height (Optional[int], optional): Desired height of the video frames.
                If None, uses default or calculates based on `width`.
        """

        if not self.camera_run:
            self.start_camera(fps, width, height)

        counter = 0

        while True:
            if self.stream_img is not None:
                break
            if counter <= 1:
                self.logger.debug("waiting for stream img")
            counter += 1
            await asyncio.sleep(0.1)

    def detection_process_func(self):
        """
        Function run in a separate process to perform object detection on video frames.

        Continuously retrieves frames from `frame_queue`, processes them using the current
        detection function, and puts the detection results into `detection_queue`.
        Listens for control messages on `control_queue` to update the detection mode or
        perform other control actions.

        The detection function depends on `video_feed_detect_mode` and is dynamically updated
        when control messages are received.

        Note:
            This function runs indefinitely until `camera_run` is set to False or the process
            is terminated.
        """
        from app.config.detectors import detectors

        current_detect_mode = self.video_feed_detect_mode
        detection_function = (
            detectors.get(current_detect_mode) if current_detect_mode else None
        )

        while self.camera_run:
            try:
                while True:
                    control_message = self.control_queue.get_nowait()
                    if control_message.get("command") == "set_detect_mode":
                        current_detect_mode = control_message.get("mode")
                        self.logger.info(
                            f"Detection mode changed to {current_detect_mode}"
                        )
                        detection_function = (
                            detectors.get(current_detect_mode)
                            if current_detect_mode
                            else None
                        )
            except queue.Empty:
                pass

            if detection_function is None:
                continue

            try:
                frame = self.frame_queue.get(timeout=1)
                detection_result = detection_function(frame)
                try:
                    self.detection_queue.put_nowait(detection_result)
                except queue.Full:
                    pass
            except queue.Empty:
                pass
            except Exception as e:
                self.logger.error(f"Error in detection_process_func: {e}")

            if not self.camera_run:
                break

        self.logger.info("Detection process exiting")

    async def generate_video_stream_for_websocket(
        self, websocket: WebSocketServerProtocol
    ):
        """
        Generates a video frame for streaming.

        Retrieves the latest detection results, overlays detection annotations onto the frame,
        applies any video enhancements, encodes the frame in the specified format, and returns
        it as a byte array ready for streaming.

        Returns:
            Optional[bytes]: The encoded video frame as a byte array, or None if no frame is available.
        """

        await self.start_camera_and_wait_for_stream_img()
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
                        self.logger.debug("Stream image is None, skipping frame.")
                        skip_count += 1
                await asyncio.sleep(0)
        finally:
            self.active_clients -= 1
            self.logger.info(
                f"generate_video_stream: Active Clients: {self.active_clients}"
            )
            if self.active_clients == 0:
                self.stop_camera()

    def camera_thread_func(self):
        """
        Starts the camera capture thread and the detection process.

        Configures the camera settings, initializes queues, and starts the threads and processes
        necessary for capturing and processing video frames.

        Args:
            fps (Optional[int], optional): Target frames per second for video capture.
                If None, uses the existing `target_fps` value.
            width (Optional[int], optional): Desired width of the video frames.
                If None, calculates based on `height` and target aspect ratio.
            height (Optional[int], optional): Desired height of the video frames.
                If None, uses default or calculates based on `width`.
        """

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
                        if self.cap:
                            self.cap.release()

                        cap = (
                            self.video_device_manager.find_and_setup_alternative_camera(
                                fps=self.target_fps,
                                width=self.frame_width,
                                height=self.frame_height,
                            )
                        )
                        if cap is None:
                            break

                        self.cap = cap

                        failed_counter = 0
                        continue
                else:
                    failed_counter = 0

                self.frame_counter += 1

                self.img = frame
                self.stream_img = frame
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    pass

        except Exception as e:
            self.logger.error(f"Exception occurred in camera loop: {e}")
        finally:
            self.cap.release()
            self.cap = None
            self.stream_img = None

            self.logger.info("Camera loop terminated and camera released.")

    def stop_camera(self):
        """
        Stops the camera capture and detection processes.

        Sets `camera_run` to False, waits for the capture thread and detection process
        to terminate, and performs any necessary cleanup of resources.
        """
        self.logger.info("Closing camera")
        self.camera_run = False
        if hasattr(self, "capture_thread") and self.capture_thread.is_alive():
            self.capture_thread.join()

        if hasattr(self, "detection_process") and self.detection_process.is_alive():
            self.detection_process.terminate()
            self.detection_process.join()
