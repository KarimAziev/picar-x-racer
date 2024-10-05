import asyncio
import collections
import os
import queue
import threading
import time
from typing import TYPE_CHECKING, Optional, Union

import cv2
import numpy as np
from app.adapters.video_device_adapter import VideoDeviceAdapater
from app.config.paths import DEFAULT_VIDEOS_PATH
from app.config.video_enhancers import frame_enhancers
from app.services.detection_service import DetectionService
from app.util.logger import Logger
from app.util.overlay_detecton import overlay_detection
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
        self._video_feed_fps = self.file_manager.settings.get("video_feed_fps", 30)
        self.video_feed_enhance_mode: Optional[str] = self.file_manager.settings.get(
            "video_feed_enhance_mode"
        )
        self.video_feed_quality = self.file_manager.settings.get(
            "video_feed_quality", 100
        )
        self.video_feed_format = self.file_manager.settings.get(
            "video_feed_format", ".jpg"
        )

        self._video_feed_record = self.file_manager.settings.get(
            "video_feed_record", False
        )

        self.video_feed_width: Optional[int] = None
        self.video_feed_height: Optional[int] = None

        self.video_writer: Optional[cv2.VideoWriter] = None

        self.frame_timestamps = collections.deque(maxlen=30)
        self.actual_fps = None

        self.camera_run = False
        self.img: Optional[np.ndarray] = None
        self.stream_img: Optional[np.ndarray] = None
        self.cap: Union[VideoCapture, None] = None
        self.last_detection_result = None

    async def generate_frame(self, log: Optional[bool] = False):
        """
        Generates a video frame for streaming.

        Retrieves the latest detection results, overlays detection annotations onto the frame,
        applies any video enhancements, encodes the frame in the specified format, and returns
        it as a byte array ready for streaming.

        Args:
            log (Optional[bool]): Indicates whether to log the detection result (default is False).

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

            if log and self.video_feed_enhance_mode:
                self.logger.info(f"Detection result: {self.last_detection_result}")

        if self.stream_img is not None:
            format = self.video_feed_format

            video_feed_quality = self.video_feed_quality
            frame = self.stream_img.copy()
            if (
                self.last_detection_result is not None
                and self.detection_service.video_feed_detect_mode is not None
            ):
                frame = overlay_detection(frame, self.last_detection_result)

            encode_params = (
                [cv2.IMWRITE_JPEG_QUALITY, video_feed_quality]
                if format == ".jpg"
                else []
            )

            encoded_frame = encode(frame, format, encode_params)

            return encoded_frame

    def camera_thread_func(self):
        """
        Camera capture loop function.

        Manages the process of capturing video frames, enhancing them, and
        pushing them to the detection service. Handles errors and device resets.
        """

        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception as e:
            self.logger.log_exception(
                f"Exception occurred while stopping camera capture", e
            )
        finally:
            self.cap = None

        self.cap = self.video_device_adapter.setup_video_capture()

        if not self.cap:
            return

        self.logger.info(
            f"CAP backend {self.cap.getBackendName()} fps {self.video_feed_fps}"
        )

        # self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        # Later, you can check and verify:
        actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        print(f"Width: {actual_width}, Height: {actual_height}, FPS: {actual_fps}")

        failed_counter = 0

        max_failed_attempt_count = 10

        try:
            while self.camera_run and self.cap:
                frame_start_time = time.time()
                ret, frame = self.cap.read()
                if not ret:
                    if failed_counter < max_failed_attempt_count:
                        failed_counter += 1
                        self.logger.error("Failed to read frame from camera.")
                        continue
                    else:
                        (video_device, _) = self.video_device_adapter.video_device or (
                            None,
                            None,
                        )
                        if video_device:
                            self.video_device_adapter.failed_camera_devices.append(
                                video_device
                            )

                        if self.cap:
                            self.cap.release()

                        cap = self.video_device_adapter.setup_video_capture()
                        if cap is None:
                            break

                        self.cap = cap
                        self.cap.set(cv2.CAP_PROP_FPS, self.video_feed_fps)
                        continue
                else:
                    failed_counter = 0
                    self.frame_timestamps.append(frame_start_time)
                    if len(self.frame_timestamps) >= 2:
                        time_diffs = [
                            t2 - t1
                            for t1, t2 in zip(
                                self.frame_timestamps, list(self.frame_timestamps)[1:]
                            )
                        ]
                        avg_time_diff = sum(time_diffs) / len(time_diffs)
                        self.actual_fps = (
                            1.0 / avg_time_diff if avg_time_diff > 0 else None
                        )
                        self.logger.info(f"FPS: {self.actual_fps}")

                frame_enhancer = (
                    frame_enhancers.get(self.video_feed_enhance_mode)
                    if self.video_feed_enhance_mode
                    else None
                )

                self.img = frame
                self.stream_img = frame if not frame_enhancer else frame_enhancer(frame)
                if self.video_feed_record and self.video_writer is not None:
                    self.video_writer.write(self.stream_img)
                if self.detection_service.video_feed_detect_mode:
                    self.current_frame_timestamp = time.time()

                    frame_data = {
                        "frame": self.stream_img.copy(),
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
            if self.video_feed_record:
                self.video_feed_record = False

            self.logger.info("Camera loop terminated and camera released.")

    def start_camera(self):
        """
        Starts the camera capture thread and the detection process.

        Checks if the camera is already running and prevents multiple starts.
        """
        if self.camera_run:
            self.logger.info("Camera is already running.")
            return

        self.camera_run = True
        self.capture_thread = threading.Thread(target=self.camera_thread_func)
        self.capture_thread.start()
        if self.detection_service.video_feed_detect_mode:
            self.detection_service.start_detection_process()

    async def start_camera_and_wait_for_stream_img(self):
        """
        Asynchronously starts the camera and waits until the first frame is available.

        Useful for ensuring that the camera is ready and frames are available before
        starting operations that depend on the video stream.

        """

        if not self.camera_run:
            self.start_camera()

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
        self.last_detection_result = None
        self.camera_run = False
        if hasattr(self, "capture_thread") and self.capture_thread.is_alive():
            self.logger.info("Stopping camera capture thread")
            self.capture_thread.join()
            self.logger.info("Stopped camera capture thread")

    @property
    def video_feed_fps(self) -> int:
        return self._video_feed_fps

    @video_feed_fps.setter
    def video_feed_fps(self, value: int):
        if self._video_feed_fps != value:
            self._video_feed_fps = value
            self.logger.info(f"FPS setting to {value}")
            if self.cap:
                self.cap.set(cv2.CAP_PROP_FPS, value)
                self.logger.info(f"FPS setted to {value}")

    @property
    def video_feed_record(self) -> bool:
        """
        Gets or sets the state of video recording.

        When set to True, video recording starts and video will be saved to the predefined path.
        When set to False, video recording stops.

        Returns:
            bool: The current state of video recording.
        """
        return self._video_feed_record

    @video_feed_record.setter
    def video_feed_record(self, value: bool):
        if self._video_feed_record != value:
            self._video_feed_record = value
            if value:
                self.start_video_recording()
            else:
                self.stop_video_recording()

    def start_video_recording(self):
        """
        Starts recording video to the specified path. Ensures the directory exists.
        """
        if not os.path.exists(DEFAULT_VIDEOS_PATH):
            os.makedirs(DEFAULT_VIDEOS_PATH)

        fps = (
            self.actual_fps
            if self.actual_fps is not None
            else self.video_feed_fps or 30
        )

        name = f"recording_{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}.avi"
        video_path = os.path.join(DEFAULT_VIDEOS_PATH, name)

        shape = (
            self.stream_img.shape[:2]
            if self.stream_img is not None
            else (self.img.shape[:2] if self.img is not None else None)
        )
        (height, width) = (
            shape
            if shape is not None
            else (
                self.video_feed_height or 480,
                self.video_feed_width or 640,
            )
        )
        self.logger.info(
            f"Starting video recording {width}x{height} with {fps} at {video_path}"
        )

        fourcc = cv2.VideoWriter.fourcc(*"XVID")
        self.video_writer = cv2.VideoWriter(
            video_path,
            fourcc,
            fps,
            (
                width,
                height,
            ),
        )

    def stop_video_recording(self):
        """
        Stops recording video and releases resources.
        """
        if self.video_writer is not None:
            self.video_writer.release()
            self.video_writer = None
            self.logger.info("Stopped video recording")


if __name__ == "__main__":
    from app.services.audio_service import AudioService
    from app.services.detection_service import DetectionService
    from app.services.files_service import FilesService

    audio_manager = AudioService()
    file_manager = FilesService(audio_manager=audio_manager)
    detection_manager = DetectionService(file_manager=file_manager)

    camera_service = CameraService(
        file_manager=file_manager, detection_service=detection_manager
    )

    camera_service.camera_run = True
    camera_service.camera_thread_func()
