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
from app.exceptions.camera import (
    CameraDeviceError,
    CameraNotFoundError,
    CameraRecordingError,
)
from app.schemas.camera import CameraSettings
from app.schemas.stream import StreamSettings
from app.util.device import parse_v4l2_device_info
from app.util.logger import Logger
from app.util.overlay_detecton import overlay_fps_render
from app.util.singleton_meta import SingletonMeta
from app.util.video_utils import calc_fps, encode, resize_to_fixed_height

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.detection_service import DetectionService
    from app.services.files_service import FilesService


class CameraService(metaclass=SingletonMeta):
    """
    The `CameraService` singleton class manages camera operations, video streaming,
    and object detection functionality. It handles starting and stopping the camera,
    capturing frames, streaming video to clients, and processing object detection in
    a separate process.
    """

    def __init__(
        self,
        detection_service: "DetectionService",
        file_manager: "FilesService",
        connection_manager: "ConnectionService",
    ):
        """
        Initializes the `CameraService` singleton instance.
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
        self.connection_manager = connection_manager

        self.current_frame_timestamp = None

        self.video_writer: Optional[cv2.VideoWriter] = None
        self.actual_fps = None

        self.camera_run = False
        self.img: Optional[np.ndarray] = None
        self.stream_img: Optional[np.ndarray] = None
        self.cap: Union[cv2.VideoCapture, None] = None
        self.cap_lock = threading.Lock()
        self.asyncio_cap_lock = asyncio.Lock()

    async def update_camera_settings(self, settings: CameraSettings) -> CameraSettings:
        """
        Updates the camera's settings and handles device initialization with retries.

        This method adjusts the camera settings such as resolution, FPS, or pixel format based
        on the provided `settings`. If the specified `device` in the new settings fails during
        initialization, the method attempts to find and configure an alternate device. The updated
        settings, including any fallback device, are then applied.

        Key Behaviors:
        - If the incoming `settings.device` is invalid or fails, the service resets the `device` field
          to `None` and attempts to initialize an alternate available camera device.
          Upon success, `self.camera_settings.device` is updated with the new device.
        - The camera is restarted (stopped and reinitialized) to apply the updated settings.

        Broadcast Behavior:
        - The updated `self.camera_settings` is provided as the return value to allow the caller
          (e.g., an external service or API endpoint) to broadcast the new settings to connected clients.
        - In the case of a fallback or retry (where the specified device fails and another device is found),
          the updated settings — including the new fallback device — will reflect this change.

        Workflow:
        1. Updates the internal `self.camera_settings` with the new settings.
        2. Attempts to restart the camera to apply the updated settings.
        3. If `settings.device` fails during initialization:
           - Resets `settings.device` to `None`.
           - Searches for and configures another available device.
           - Updates `self.camera_settings.device` with the alternate device if initialization succeeds.
        4. Returns the finalized and applied `self.camera_settings`.

        Args:
            settings (CameraSettings): The new camera settings to apply.

        Returns:
            CameraSettings: The fully updated camera settings, including any modified `device`
            if a fallback occurred.

        Raises:
            CameraDeviceError: If the specified camera device cannot be initialized, and no alternate
                               device is available.
            Exception: If camera restart or other operations fail unexpectedly.
        """
        self.camera_settings = settings
        await self.restart_camera()
        return self.camera_settings

    async def update_stream_settings(self, settings: StreamSettings) -> StreamSettings:
        """
        Updates the stream settings and handles camera restarts if necessary.

        This method modifies various stream settings such as file format, quality,
        frame enhancers, and video recording preferences. If video recording is enabled in
        the new settings while it was previously disabled, the camera is restarted to
        apply the new configuration properly.

        Key Behaviors:
        - Updates the internal `self.stream_settings` with the provided settings.
        - Detects changes requiring a camera restart — specifically if `video_record` is
          enabled in the new settings but was previously disabled.
        - Avoids unnecessary restarts for other settings changes, ensuring minimal disruption.

        Workflow:
        1. Evaluates whether the `video_record` field has transitioned from `False` to `True`.
           - If true, a camera restart is triggered to ensure the recording configuration
             is applied correctly.
        2. The method applies the new stream settings by updating `self.stream_settings`.
        3. Returns the updated `self.stream_settings` to allow broadcasting to connected clients.

        Broadcast Behavior:
        - While this method does not directly perform broadcasting, the updated
          `self.stream_settings` data can be returned to external services or
          APIs (e.g., via `ConnectionService`) for broadcasting to clients.
        - Any subsequent changes to the stream settings will reflect these updates.

        Args:
            settings (StreamSettings): The new streaming configuration to apply.

        Returns:
            StreamSettings: The updated streaming settings.

        Raises:
            Exception: If the camera restart fails or unexpected issues occur during configuration.
        """
        should_restart = settings.video_record and not self.stream_settings.video_record
        self.stream_settings = settings
        if should_restart:
            await self.restart_camera()
        return self.stream_settings

    def generate_frame(self) -> Optional[bytes]:
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

    def setup_camera_props(self) -> None:
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

        self.stop_video_recording()

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
                try:
                    self.start_video_recording()
                except CameraRecordingError as e:
                    self.logger.error(str(e))
                except Exception:
                    self.logger.error(
                        "Unhandled error while starting video recording", exc_info=True
                    )

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

    def _release_cap_safe(self) -> None:
        """
        Safely releases the camera resource represented by `self.cap`.
        """
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception:
            self.logger.log_exception(
                "Exception occurred while stopping camera capture"
            )
        finally:
            self.cap = None

    def _retry_cap(self) -> Optional[cv2.VideoCapture]:
        """
        Attempts to reinitialize the camera by retrying the video capture setup.

        This method is called when the current video capture device (`self.cap`) encounters an error
        or fails to read frames. It performs the following operations:
        - Marks the current camera device as "failed" and appends it to a list of failed devices.
        - Releases the current video capture device (`self.cap`) safely to free resources.
        - Attempts to find and set up another available camera device using `VideoDeviceAdapter`.

        If a new camera device is successfully initialized, its properties are configured using
        `setup_camera_props`. If no valid camera device is found, the method returns `None`.

        Returns:
            Optional[cv2.VideoCapture]: A new valid video capture object if setup succeeds, or `None`.
        """
        (video_device, _) = self.video_device_adapter.video_device or (
            None,
            None,
        )
        if video_device:
            self.video_device_adapter.failed_camera_devices.append(video_device)

        if self.cap:
            try:
                self.cap.release()
            except Exception:
                self.logger.error("Error releasing failed video capture", exc_info=True)

        self.cap = self.video_device_adapter.setup_video_capture()

        if self.cap is not None:
            self.setup_camera_props()
        return self.cap

    def _camera_thread_func(self) -> None:
        """
        Camera capture loop function.

        Manages the process of capturing video frames, enhancing them, and
        pushing them to the detection service. Handles errors and device resets.
        """
        failed_counter = 0
        max_failed_attempt_count = 10

        prev_fps = 0.0

        self.frame_timestamps: collections.deque[float] = collections.deque(maxlen=30)

        try:
            while self.camera_run and self.cap:
                frame_start_time = time.time()
                ret, frame = self.cap.read()
                if not ret:
                    if failed_counter < max_failed_attempt_count:
                        failed_counter += 1
                        self.logger.error("Failed to read frame from camera.")
                        continue
                    elif self._retry_cap():
                        continue
                    else:
                        break
                else:
                    failed_counter = 0

                    self.frame_timestamps.append(frame_start_time)

                    self.actual_fps = calc_fps(self.frame_timestamps)
                    if (
                        self.actual_fps is not None
                        and abs(self.actual_fps - prev_fps) > 1
                    ):
                        self.logger.info("FPS: %s", self.actual_fps)
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
        except Exception:
            self.logger.error(
                "Unhandled exception occurred in camera loop", exc_info=True
            )
        finally:
            self._release_cap_safe()
            self.stream_img = None
            self.stop_video_recording()
            self.logger.info("Camera loop terminated and camera released.")

    def _start_camera(self) -> None:
        """
        Configures and starts the camera capture thread.

        This method initializes the video capture device based on the current
        settings and prepares it for frame capturing. It ensures that the existing
        capture resource is released before assigning a new device and thread.

        Actions performed:
        - Releases any previously active camera device.
        - Sets up the camera device based on the current configuration.
        - Applies camera properties like resolution, FPS, and pixel format.
        - Starts a dedicated thread to run the capture loop.

        Raises:
            Exception: If an error occurs during setup or thread initialization.

        Returns:
            None
        """

        with self.cap_lock:
            if self.camera_run:
                self.logger.info("Camera is already running.")
                return
            self.camera_run = True
            try:
                self._release_cap_safe()

                if self.camera_settings.device is not None:
                    self.cap = self.video_device_adapter.update_device(
                        self.camera_settings.device
                    )
                else:
                    self.cap = self.video_device_adapter.find_and_setup_device_cap()
                self.setup_camera_props()
                self.capture_thread = threading.Thread(target=self._camera_thread_func)
                self.capture_thread.start()

            except Exception as e:
                self.camera_run = False
                raise e

    async def start_camera_and_wait_for_stream_img(self):
        """
        Starts the camera asynchronously and ensures it is ready for streaming.

        If a camera device is specified in the settings but fails to initialize, this method resets
        the device in the settings and makes *one* additional attempt to find another available device
        and set it in the settings upon success.

        If the specified camera device is invalid, it resets the device and attempts to
        find and initialize another available device.

        Raises:
            CameraDeviceError: If the chosen camera encounters initialization errors.
            CameraNotFoundError: If no valid camera device is found after retries.

        Returns:
            None
        """

        async with self.asyncio_cap_lock:
            if not self.camera_run:
                try:
                    await asyncio.to_thread(self._start_camera)
                except CameraDeviceError as err:
                    if self.camera_settings.device:
                        await self.connection_manager.error(
                            f"Camera device {self.camera_settings.device} error: {err}, trying to find other camera"
                        )
                        self.camera_settings.device = None
                        try:
                            await asyncio.to_thread(self._start_camera)
                            await self.connection_manager.broadcast_json(
                                {
                                    "type": "camera",
                                    "payload": self.camera_settings.model_dump(),
                                }
                            )
                        except CameraNotFoundError as e:
                            await self.connection_manager.error(str(e))
                            raise e

        counter = 0

        while True:
            if self.stream_img is not None:
                break
            if counter <= 1:
                self.logger.debug("waiting for stream img")
                counter += 1
            await asyncio.sleep(0.1)

    def stop_camera(self) -> None:
        """
        Gracefully stops the camera capture thread and cleans up associated resources.

        Returns:
            None
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

    def start_video_recording(self) -> None:
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

    def stop_video_recording(self) -> None:
        """
        Stops recording video and releases resources.
        """
        if self.video_writer is not None:
            self.logger.info("Stopping video recording")
            try:
                self.video_writer.release()
                self.video_writer = None
                self.logger.info("Stopped video recording")
            except Exception:
                self.logger.error(
                    "Exception occurred while stopping camera recording capture",
                    exc_info=True,
                )

    async def restart_camera(self) -> None:
        """
        Restarts the camera by stopping and reinitializing it.

        This method first stops the current camera capture process to release
        resources and reset the camera's state. It then calls
        `start_camera_and_wait_for_stream_img` to begin a new capture session.

        It can be used for dynamically changing camera settings or recovering from
        errors while the system remains operational.

        Returns:
            None
        """
        cam_running = self.camera_run
        if cam_running:
            await asyncio.to_thread(self.stop_camera)
        if cam_running:
            await self.start_camera_and_wait_for_stream_img()
