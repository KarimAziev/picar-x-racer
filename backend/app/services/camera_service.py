import asyncio
import queue
import threading
import time
from typing import TYPE_CHECKING, Optional, Union

import cv2
import numpy as np
from app.adapters.video_device_adapter import VideoDeviceAdapater
from app.config.video_enhancers import frame_enhancers
from app.services.detection_service import DetectionService
from app.util.logger import Logger
from app.util.overlay_detecton import overlay_detection
from app.util.photo import height_to_width
from app.util.singleton_meta import SingletonMeta
from app.util.video_utils import encode
from cv2 import VideoCapture

if TYPE_CHECKING:
    from app.services.files_service import FilesService

# Constants for target width and height of video streams
TARGET_WIDTH = 320
TARGET_HEIGHT = 240


class CameraService(metaclass=SingletonMeta):
    """
    The `CameraService` singleton class manages camera operations, video streaming,
    and object detection functionality. It handles starting and stopping the camera,
    capturing frames, streaming video to clients, and processing object detection in
    a separate process.
    """

    def __init__(
        self, detection_service: DetectionService, file_manager: "FilesService"
    ):
        """
        Initializes the `CameraService` singleton instance.

        Args:
            detection_service: DetectionService
        """
        self.logger = Logger(name=__name__)
        self.file_manager = file_manager
        self.detection_service = detection_service
        self.video_device_adapter = VideoDeviceAdapater()
        self.video_feed_fps = self.file_manager.settings.get("video_feed_fps", 30)
        self.video_feed_enhance_mode: Optional[str] = self.file_manager.settings.get(
            "video_feed_enhance_mode"
        )
        self.video_feed_quality = self.file_manager.settings.get(
            "video_feed_quality", 100
        )
        self.video_feed_format = self.file_manager.settings.get(
            "video_feed_format", ".jpg"
        )
        self.video_feed_confidence = self.file_manager.settings.get(
            "video_feed_confidence"
        )
        self.video_feed_width: Optional[int] = None
        self.video_feed_height: Optional[int] = None

        self.camera_run = False
        self.img: Optional[np.ndarray] = None
        self.stream_img: Optional[np.ndarray] = None
        self.cap: Union[VideoCapture, None] = None
        self.last_detection_result = None
        self.cap_task = None

    async def generate_frame(self):
        """
        Generates a video frame for streaming.

        Retrieves the latest detection results, overlays detection annotations onto the frame,
        applies any video enhancements, encodes the frame in the specified format, and returns
        it as a byte array ready for streaming.

        Returns:
            Optional[bytes]: The encoded video frame as a byte array, or None if no frame is available.
        """

        latest_detection = None
        while True:
            try:
                detection_data = self.detection_service.detection_queue.get_nowait()
                detection_timestamp = detection_data["timestamp"]
                if detection_timestamp <= self.current_frame_timestamp:
                    latest_detection = detection_data["detection_result"]
                else:
                    self.detection_service.detection_queue.put_nowait(detection_data)
                    break
            except queue.Empty:
                break

            self.last_detection_result = latest_detection

        if self.stream_img is not None:
            format = self.video_feed_format
            video_feed_enhance_mode = self.video_feed_enhance_mode
            video_feed_quality = self.video_feed_quality
            frame = self.stream_img.copy()
            if (
                self.last_detection_result is not None
                and self.detection_service.video_feed_detect_mode is not None
            ):
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
            encoded_frame = encode(frame, format, encode_params, frame_enhancer)

            return encoded_frame

    def camera_thread_func(self):
        """
        Starts the camera capture thread and the detection process.

        Configures the camera settings, initializes queues, and starts the threads and processes
        necessary for capturing and processing video frames.

        Args:
            fps (Optional[int], optional): Target frames per second for video capture.
                If None, uses the existing `video_feed_fps` value.
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
            f"Starting camera loop with camera index {self.video_device_adapter.camera_index}"
        )
        self.cap = self.video_device_adapter.setup_video_capture(
            fps=self.video_feed_fps,
            width=self.video_feed_width,
            height=self.video_feed_height,
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
                        self.video_device_adapter.failed_camera_indexes.append(
                            self.video_device_adapter.camera_index
                        )
                        if self.cap:
                            self.cap.release()

                        cap = (
                            self.video_device_adapter.find_and_setup_alternative_camera(
                                fps=self.video_feed_fps,
                                width=self.video_feed_width,
                                height=self.video_feed_height,
                            )
                        )
                        if cap is None:
                            break

                        self.cap = cap
                        self.img = frame
                        self.stream_img = frame

                        failed_counter = 0
                        continue
                else:
                    failed_counter = 0

                self.img = frame
                self.stream_img = frame
                if self.detection_service.video_feed_detect_mode:
                    self.current_frame_timestamp = time.time()

                    frame_data = {
                        "frame": frame.copy(),
                        "timestamp": self.current_frame_timestamp,
                    }
                    self.detection_service.put_frame(frame_data)

        except Exception as e:
            self.logger.log_exception("Exception occurred in camera loop", e)
        finally:
            if self.cap is not None:
                self.cap.release()

            self.cap = None
            self.stream_img = None

            self.logger.info("Camera loop terminated and camera released.")

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
                If None, uses the existing `video_feed_fps` value.
            width (Optional[int], optional): Desired width of the video frames.
                If None, calculates based on `height` and target aspect ratio.
            height (Optional[int], optional): Desired height of the video frames.
                If None, uses default or calculates based on `width`.
        """
        if self.camera_run:
            self.logger.info("Camera is already running.")
            return

        if fps:
            self.video_feed_fps = fps

        self.logger.info(f"Starting camera")
        self.video_feed_height = height
        self.video_feed_width = width or (
            height_to_width(height, TARGET_WIDTH, TARGET_HEIGHT) if height else None
        )

        self.camera_run = True
        self.capture_thread = threading.Thread(target=self.camera_thread_func)
        self.capture_thread.start()
        if self.detection_service.video_feed_detect_mode:
            self.detection_service.start_detection_process()

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
                If None, uses the existing `video_feed_fps` value.
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

    def stop_camera(self):
        """
        Stops the camera capture and detection processes.

        Sets `camera_run` to False, waits for the capture thread and detection process
        to terminate, and performs any necessary cleanup of resources.
        """
        if not self.camera_run:
            self.logger.info("Camera is not running.")
            return
        self.logger.info("Stopping camera")
        self.camera_run = False
        if hasattr(self, "capture_thread") and self.capture_thread.is_alive():
            self.logger.info("Stopping camera capture thread")
            self.capture_thread.join()
            self.logger.info("Stopped camera capture thread")
        self.detection_service.stop_detection_process()
        self.detection_service.clear_stop_event()
