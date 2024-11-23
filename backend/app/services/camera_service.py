import asyncio
import collections
import os
import struct
import threading
import time
from typing import TYPE_CHECKING, Optional, Union

import cv2
import numpy as np
from app.adapters.video_device_adapter import VideoDeviceAdapater
from app.config.video_enhancers import frame_enhancers
from app.exceptions.camera import CameraRecordingError
from app.schemas.camera import CameraSettings
from app.schemas.stream import StreamSettings
from app.services.detection_service import DetectionService
from app.util.device import parse_v4l2_device_info
from app.util.logger import Logger
from app.util.overlay_detecton import overlay_fps_render
from app.util.singleton_meta import SingletonMeta
from app.util.video_utils import encode, resize_to_fixed_height

if TYPE_CHECKING:
    from app.services.files_service import FilesService


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
        self.camera_settings = CameraSettings(
            **self.file_manager.settings.get("camera", {})
        )
        self.stream_settings = StreamSettings(
            **self.file_manager.settings.get("stream", {})
        )
        self.video_device_adapter = VideoDeviceAdapater()

        self.current_frame_timestamp = None

        self.video_writer: Optional[cv2.VideoWriter] = None
        self.actual_fps = None

        self.camera_run = False
        self.img: Optional[np.ndarray] = None
        self.stream_img: Optional[np.ndarray] = None
        self.cap: Union[cv2.VideoCapture, None] = None
        self.last_detection_result = None

    def update_camera_settings(self, settings: CameraSettings):
        self.camera_settings = settings
        self.restart_camera()
        return self.camera_settings

    def update_stream_settings(self, settings: StreamSettings):
        self.stream_settings = settings
        return self.stream_settings

    def generate_frame(self):
        """
        Generates a video frame for streaming, including an embedded timestamp.

        Retrieves the latest detection results, optionally overlays FPS rendering on the frame,
        encodes the frame in the specified format, and returns it as a byte array along with the
        timestamp.

        The timestamp is packed in binary format (double-precision float), and it is prepended to the encoded frame.

        Returns:
            Optional[bytes]: The encoded video frame as a byte array, prefixed by the frame's
                             timestamp (as double-precision floating point format), or None if no
                             frame is available.
        """
        if self.stream_img is not None:
            frame = (
                overlay_fps_render(self.stream_img, self.actual_fps)
                if self.stream_settings.render_fps and self.actual_fps
                else self.stream_img
            )

            encode_params = (
                [cv2.IMWRITE_JPEG_QUALITY, self.stream_settings.quality]
                if self.stream_settings.format == ".jpg"
                else []
            )

            encoded_frame = encode(frame, self.stream_settings.format, encode_params)

            timestamp = self.current_frame_timestamp or time.time()
            timestamp_bytes = struct.pack('d', timestamp)

            return timestamp_bytes + encoded_frame

    def setup_camera_props(self):
        """
        Configure the camera properties such as FPS, resolution (width and height),
        and pixel format based on the current settings and device information.

        This method initializes and sets key camera parameters, including:
        - Pixel format if provided.
        - Frame width and height.
        - Frame rate (FPS).

        Updates:
            - `self.camera_settings.fps`: Frames per second setting of the video feed.
            - `self.camera_settings.width`: Width of the video frame.
            - `self.camera_settings.height`: Height of the video frame.
            - `self.camera_settings.pixel_format`: Pixel format based on device information.
        """
        if self.video_writer is not None:
            try:
                self.stop_video_recording()
            except Exception as e:
                self.logger.error(
                    f"Exception occurred while stopping camera recording capture", e
                )

        if self.cap is not None:
            info = self.video_device_adapter.video_device or (None, None)
            (self.camera_settings.device, _) = info

            for field_name, field_value in self.camera_settings.model_dump(
                exclude_unset=True
            ).items():
                field_info = self.camera_settings.model_fields[field_name]
                field_title = field_info.title if field_info.title else field_name
                self.logger.info(f"Updating {field_title}: {field_value}")

            if self.camera_settings.pixel_format:
                self.cap.set(
                    cv2.CAP_PROP_FOURCC,
                    cv2.VideoWriter.fourcc(*self.camera_settings.pixel_format),
                )

            if self.camera_settings.width is not None:
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_settings.width)

            if self.camera_settings.height is not None:
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_settings.height)

            if self.camera_settings.fps is not None:
                self.cap.set(cv2.CAP_PROP_FPS, float(self.camera_settings.fps))

            width, height, fps = (
                int(self.cap.get(x))
                for x in (
                    cv2.CAP_PROP_FRAME_WIDTH,
                    cv2.CAP_PROP_FRAME_HEIGHT,
                    cv2.CAP_PROP_FPS,
                )
            )
            self.camera_settings.width = width
            self.camera_settings.height = height
            self.camera_settings.fps = fps

            if self.stream_settings.video_record:
                self.start_video_recording()

            self.logger.info(
                "Updated size: %sx%s, FPS: %s",
                width,
                height,
                fps,
            )
            if self.camera_settings.device:
                data = parse_v4l2_device_info(self.camera_settings.device)
                self.camera_settings.pixel_format = data.get(
                    "pixel_format", self.camera_settings.pixel_format
                )

    def release_cap_safe(self):
        """
        Safely releases the camera resource represented by `self.cap`.

        This method checks whether the camera capture object (`self.cap`) is initialized and open.
        If so, it releases the camera resource, ensuring no further frames are captured.

        This method also handles potential exceptions that may occur while releasing
        the camera resource by logging the exception via `self.logger`.

        After releasing the camera, the `self.cap` object is set to `None`.
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

    def camera_thread_func(self):
        """
        Camera capture loop function.

        Manages the process of capturing video frames, enhancing them, and
        pushing them to the detection service. Handles errors and device resets.
        """

        self.release_cap_safe()
        self.cap = self.video_device_adapter.setup_video_capture()

        if not self.cap:
            self.logger.warning("Couldn't setup video capture")
            return

        self.setup_camera_props()

        failed_counter = 0

        max_failed_attempt_count = 10
        prev_fps = 0.0

        self.frame_timestamps = collections.deque(maxlen=30)

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
                        self.logger.info(
                            "Setting size to: %sx%s",
                            self.camera_settings.width,
                            self.camera_settings.height,
                        )
                        self.setup_camera_props()
                        self.logger.info(
                            "Updated size: %sx%s",
                            self.cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                            self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT),
                        )
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

                        if self.actual_fps is not None:
                            diff = self.actual_fps - prev_fps
                            if abs(diff) >= 2:
                                self.logger.info(
                                    "Real FPS %s",
                                    self.actual_fps,
                                )
                                prev_fps = self.actual_fps

                enhance_mode = self.stream_settings.enhance_mode
                frame_enhancer = (
                    frame_enhancers.get(enhance_mode)
                    if enhance_mode is not None
                    else None
                )

                self.img = frame
                self.stream_img = frame if not frame_enhancer else frame_enhancer(frame)

                if self.video_writer is not None:
                    self.video_writer.write(self.stream_img)
                if (
                    self.detection_service.detection_settings.active
                    and not self.detection_service.loading
                ):
                    self.current_frame_timestamp = time.time()
                    (
                        resized_frame,
                        original_width,
                        original_height,
                        resized_width,
                        resized_height,
                    ) = resize_to_fixed_height(
                        self.stream_img.copy(),
                        base_size=self.detection_service.detection_settings.img_size,
                    )
                    frame_data = {
                        "frame": resized_frame,
                        "timestamp": self.current_frame_timestamp,
                        "original_height": original_height,
                        "original_width": original_width,
                        "resized_height": resized_height,
                        "resized_width": resized_width,
                        "should_resize": False,
                    }
                    self.detection_service.put_frame(frame_data)

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt, stopping camera loop")
        except asyncio.CancelledError:
            self.logger.info("Camera loop is cancelled")
        except Exception as e:
            self.logger.log_exception("Exception occurred in camera loop", e)
        finally:
            self.release_cap_safe()
            self.stream_img = None
            if self.video_writer is not None:
                try:
                    self.stop_video_recording()
                except Exception as e:
                    self.logger.error(
                        f"Exception occurred while stopping camera recording capture", e
                    )
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
        if not os.path.exists(self.file_manager.user_videos_dir):
            os.makedirs(self.file_manager.user_videos_dir)

        fps = (
            self.camera_settings.fps
            if self.camera_settings.fps is not None
            else self.actual_fps or 30.0
        )
        if isinstance(fps, int):
            fps = float(fps)

        name = f"recording_{time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())}.avi"
        video_path = os.path.join(self.file_manager.user_videos_dir, name)

        shape = (
            self.stream_img.shape[:2]
            if self.stream_img is not None
            else (self.img.shape[:2] if self.img is not None else None)
        )
        (height, width) = (
            shape
            if shape is not None
            else (
                self.camera_settings.height,
                self.camera_settings.width,
            )
        )

        if height is None or width is None:
            raise CameraRecordingError(
                f"Video Recording: invalid height {height} or width {width}"
            )

        self.logger.info(
            "Starting video recording %sx%s with %s at %s",
            width,
            height,
            fps,
            video_path,
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

    def restart_camera(self):
        cam_running = self.camera_run
        if cam_running:
            self.stop_camera()
        if self.camera_settings.device:
            result = self.video_device_adapter.update_device(
                self.camera_settings.device
            )
            if result is None:
                self.logger.error(
                    "Device %s is not available",
                    self.camera_settings.device,
                )
        else:
            self.video_device_adapter.video_device = None
        if cam_running:
            self.start_camera()

    def update_device(self, device: Optional[str]):
        cam_running = self.camera_run
        if cam_running:
            self.stop_camera()
        if device:
            result = self.video_device_adapter.update_device(device)
            if result is None:
                self.logger.error("Device %s is not available", device)
        else:
            self.video_device_adapter.video_device = None
        if cam_running:
            self.start_camera()
