import asyncio
import collections
import struct
import threading
import time
from typing import TYPE_CHECKING, Optional, Union

import cv2
import numpy as np
from app.config.video_enhancers import frame_enhancers
from app.core.event_emitter import EventEmitter
from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from app.managers.v4l2_manager import V4L2
from app.schemas.camera import CameraSettings
from app.schemas.stream import StreamSettings
from app.util.video_utils import calc_fps, encode, resize_to_fixed_height
from cv2.typing import MatLike

if TYPE_CHECKING:
    from app.adapters.video_device_adapter import VideoDeviceAdapater
    from app.services.connection_service import ConnectionService
    from app.services.detection_service import DetectionService
    from app.services.file_service import FileService
    from app.services.video_recorder import VideoRecorder


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
        file_manager: "FileService",
        connection_manager: "ConnectionService",
        video_device_adapter: "VideoDeviceAdapater",
        video_recorder: "VideoRecorder",
    ):
        """
        Initializes the `CameraService` singleton instance.
        """
        self.logger = Logger(name=__name__)
        self.file_manager = file_manager
        self.detection_service = detection_service
        self.video_device_adapter = video_device_adapter
        self.connection_manager = connection_manager
        self.video_recorder = video_recorder

        self.camera_settings = CameraSettings(
            **self.file_manager.settings.get("camera", {})
        )
        self.stream_settings = StreamSettings(
            **self.file_manager.settings.get("stream", {})
        )
        self.current_frame_timestamp = None

        self.actual_fps = None

        self.camera_run = False
        self.img: Optional[np.ndarray] = None
        self.stream_img: Optional[np.ndarray] = None
        self.cap: Union[cv2.VideoCapture, None] = None
        self.cap_lock = threading.Lock()
        self.asyncio_cap_lock = asyncio.Lock()
        self.shutting_down = False
        self.emitter = EventEmitter()

        self.emitter.on("frame_error", self.connection_manager.error)

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
        Generates a video frame for streaming, including an embedded timestamp and FPS.

        Encodes the video frame in the specified format and returns it as a byte array
        with additional metadata. The frame is prefixed by the frame's timestamp and FPS,
        both packed in binary format as double-precision floating-point numbers.

        The structure of the returned byte array is as follows:
            - First 8 bytes: Timestamp (double-precision float) in seconds since the epoch.
            - Next 8 bytes: FPS (double-precision float) representing the current frame rate.
            - Remaining bytes: Encoded video frame in the specified format (e.g., JPEG).

        Returns:
            The encoded video frame as a byte array, prefixed with the timestamp
            and FPS, or None if no frame is available.
        """
        if self.stream_img is not None:
            frame = self.stream_img
            encode_params = (
                [cv2.IMWRITE_JPEG_QUALITY, self.stream_settings.quality]
                if self.stream_settings.format == ".jpg"
                else []
            )

            encoded_frame = encode(frame, self.stream_settings.format, encode_params)

            timestamp = self.current_frame_timestamp or time.time()
            timestamp_bytes = struct.pack('d', timestamp)

            fps = self.actual_fps or 0.0
            fps_bytes = struct.pack('d', fps)

            return timestamp_bytes + fps_bytes + encoded_frame

    def _setup_camera_props(self) -> None:
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

        self.video_recorder.stop_recording_safe()

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
                self.cap.get(x)
                for x in (
                    cv2.CAP_PROP_FRAME_WIDTH,
                    cv2.CAP_PROP_FRAME_HEIGHT,
                    cv2.CAP_PROP_FPS,
                )
            )
            self.camera_settings.width = int(width)
            self.camera_settings.height = int(height)
            self.camera_settings.fps = int(fps)

            if self.stream_settings.video_record:
                self.video_recorder.start_recording(
                    width=self.camera_settings.width,
                    height=self.camera_settings.height,
                    fps=fps,
                )

            self.logger.info(
                "Updated size: %sx%s, FPS: %s",
                self.camera_settings.width,
                self.camera_settings.height,
                self.camera_settings.fps,
            )
            if self.camera_settings.device:
                data = V4L2.video_capture_format(self.camera_settings.device)
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

    def _process_frame(self, frame: MatLike) -> None:
        """Task run by the ThreadPoolExecutor to handle frame detection."""
        if (
            self.detection_service.detection_settings.active
            and not self.detection_service.loading
            and not self.detection_service.shutting_down
        ):
            (
                resized_frame,
                original_width,
                original_height,
                resized_width,
                resized_height,
            ) = resize_to_fixed_height(
                frame.copy(),
                base_size=self.detection_service.detection_settings.img_size,
            )

            self.current_frame_timestamp = time.time()

            frame_data = {
                "frame": resized_frame,
                "timestamp": self.current_frame_timestamp,
                "original_height": original_height,
                "original_width": original_width,
                "resized_height": resized_height,
                "resized_width": resized_width,
                "should_resize": False,
            }
            if not self.detection_service.shutting_down:
                self.detection_service.put_frame(frame_data)

    def _camera_thread_func(self) -> None:
        """
        Camera capture loop function.

        Manages the process of capturing video frames, enhancing them, and
        pushing them to the detection service. Handles errors and device resets.
        """
        failed_counter = 0
        max_failed_attempt_count = 5

        prev_fps = 0.0

        self.frame_timestamps: collections.deque[float] = collections.deque(maxlen=30)
        try:
            while self.camera_run and self.cap:
                frame_start_time = time.time()
                ret, frame = self.cap.read()
                if not ret:
                    if failed_counter < max_failed_attempt_count:
                        failed_counter += 1
                        self.emitter.emit(
                            "frame_error",
                            f"Failed to read frame from camera. {failed_counter} attempt.",
                        )
                        self.logger.error("Failed to read frame from camera.")
                        continue
                    else:
                        self.logger.error(
                            "Failed to read frame from camera, please choose another device or props."
                        )
                        self.camera_cap_error = "Failed to read frame from camera, please choose another device or props."
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
                if self.stream_settings.video_record:
                    self.video_recorder.write_frame(self.stream_img)

                self._process_frame(frame)

        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt, stopping camera loop")
        except (
            ConnectionResetError,
            BrokenPipeError,
            EOFError,
            ConnectionError,
            ConnectionRefusedError,
        ) as e:
            self.logger.warning(
                "Stopped camera loop due to connection-related error: %s",
                type(e).__name__,
            )
        except Exception:
            self.logger.error(
                "Unhandled exception occurred in camera loop", exc_info=True
            )
        finally:
            self._release_cap_safe()
            self.video_recorder.stop_recording_safe()
            self.stream_img = None
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
            CameraDeviceError: If the chosen camera encounters initialization errors.
            CameraNotFoundError: If no valid camera device is found.
            Exception: If an error occurs during setup or thread initialization.

        Returns:
            None
        """

        with self.cap_lock:
            if self.camera_run:
                self.logger.warning("Camera is already running.")
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
                self._setup_camera_props()
                self.capture_thread = threading.Thread(target=self._camera_thread_func)
                self.capture_thread.start()

            except (CameraNotFoundError, CameraDeviceError) as e:
                self.camera_run = False
                self.logger.error(str(e))
                raise

            except Exception as e:
                self.camera_run = False
                self.logger.error("Unhandled exception", exc_info=True)
                raise

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
                            f"Camera {self.camera_settings.device} error: {err}, "
                            "trying to find other camera"
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

        while not self.camera_cap_error:
            if self.stream_img is not None:
                break
            if counter <= 1:
                self.logger.debug("waiting for stream img")
                counter += 1
            await asyncio.sleep(0.1)

        if self.camera_cap_error:
            err = self.camera_cap_error
            self.camera_cap_error = None
            raise CameraDeviceError(err)

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
