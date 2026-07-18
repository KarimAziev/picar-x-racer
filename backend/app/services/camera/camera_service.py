import asyncio
import collections
import os
import threading
import time
from concurrent.futures import Future
from typing import TYPE_CHECKING, Optional, Union

import numpy as np
from app.config.video_enhancers import frame_enhancers
from app.core.event_emitter import EventEmitter
from app.core.logger import Logger
from app.core.video_capture_abc import VideoCaptureABC
from app.exceptions.camera import (
    CameraDeviceError,
    CameraNotFoundError,
    CameraShutdownInProgressError,
)
from app.schemas.camera import CameraSettings
from app.schemas.stream import StreamSettings
from app.services.media.video_converter import VideoConverter
from app.types.detection import DetectionFrameData
from app.util.photo import prepare_detection_overlay_frame
from app.util.video_utils import calc_fps, letterbox

if TYPE_CHECKING:
    from app.adapters.video_device_adapter import VideoDeviceAdapter
    from app.services.connection_service import ConnectionService
    from app.services.detection.detection_service import DetectionService
    from app.services.domain.settings_service import SettingsService
    from app.services.media.video_recorder_service import VideoRecorderService
    from cv2.typing import MatLike

_log = Logger(name=__name__)


class CameraService:
    """
    The `CameraService` manages camera operations, video streaming, and object detection
    functionality.

    It handles starting and stopping the camera, capturing frames, streaming video to
    clients, and processing object detection in a separate process.
    """

    def __init__(
        self,
        detection_service: "DetectionService",
        settings_service: "SettingsService",
        connection_manager: "ConnectionService",
        video_device_adapter: "VideoDeviceAdapter",
        video_recorder: "VideoRecorderService",
    ) -> None:
        """
        Initializes the `CameraService` instance.
        """
        self.file_manager = settings_service
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
        self.cap: Union[VideoCaptureABC, None] = None
        self._capture_thread: Optional[threading.Thread] = None
        self._camera_operation_lock = threading.RLock()
        self.frame_timestamps: collections.deque[float] = collections.deque(maxlen=30)
        self.camera_device_error: Optional[str] = None
        self.camera_loading: bool = False
        self.shutting_down = False
        self._notification_loop: Optional[asyncio.AbstractEventLoop] = None

        self.emitter = EventEmitter()

    def bind_notification_loop(self) -> None:
        try:
            self._notification_loop = asyncio.get_running_loop()
        except RuntimeError:
            return

    @staticmethod
    def _log_notification_future(
        future: Future[None],
    ) -> None:
        try:
            future.result()
        except Exception:
            _log.warning("Failed to broadcast camera error", exc_info=True)

    def _dispatch_camera_error(self, error: Optional[str]) -> None:
        self.camera_device_error = error

        loop = self._notification_loop
        if loop is None or loop.is_closed() or not loop.is_running():
            return

        future = asyncio.run_coroutine_threadsafe(
            self.notify_camera_error(error),
            loop,
        )
        future.add_done_callback(self._log_notification_future)

    async def notify_camera_error(self, error: Optional[str]) -> None:
        self.bind_notification_loop()
        self.camera_device_error = error

        await self.connection_manager.broadcast_json(
            {"type": "camera_error", "payload": error}
        )

    async def notify_video_record_end(
        self, task: asyncio.Task[Union[str, None]]
    ) -> None:
        try:
            video_file = await task
            _log.info("video_file result='%s'", video_file)
            if video_file:
                _log.info(f"Post-processing successful: {video_file}")
                rel_name = os.path.basename(video_file)
                await self.connection_manager.broadcast_json(
                    {"type": "video_record_end", "payload": rel_name}
                )
            else:
                _log.error("Video processing failed")
                await self.connection_manager.broadcast_json(
                    {"type": "video_record_error", "payload": "Video processing failed"}
                )
        except Exception:
            _log.error("Unexpected error in video processing callback:", exc_info=True)
            self.emitter.emit("video_record_error", "Video processing error")

    async def update_camera_settings(self, settings: CameraSettings) -> CameraSettings:
        """
        Updates the camera's settings and restarts the device.

        Args:
            `settings`: The new camera settings to apply.

        Returns:
            The fully updated camera settings. If certain fields failed to apply,
            the returned settings may contain modified or defaulted values.

        Raises:
        - `CameraNotFoundError`: If the specified camera device is not found in the available
          devices.
        - `CameraDeviceError`: If the specified camera device cannot be initialized and
          no alternative device is available.
        - `CameraShutdownInProgressError`: If The camera is shutting down.
        - `Exception`: If the camera restart or other related operations unexpectedly fail.
        """
        if self.shutting_down:
            _log.warning("Service is shutting down.")
            raise CameraShutdownInProgressError("The camera is shutting down.")

        self.bind_notification_loop()

        if not isinstance(settings, CameraSettings):
            settings = CameraSettings(**settings)

        self.camera_settings = settings
        await asyncio.to_thread(self.restart_camera)
        return self.camera_settings

    async def update_stream_settings(self, settings: StreamSettings) -> StreamSettings:
        """
        Updates the stream settings and restarts the camera if video recording is requested.

        This method modifies various stream settings such as file format, quality,
        frame enhancers, and video recording preferences. If video recording is enabled in
        the new settings while it was previously disabled, the camera is restarted to
        apply the new configuration properly.

        Args:
            settings: The new streaming configuration to apply.

        Returns:
            The updated streaming settings.
        """
        if self.shutting_down:
            _log.warning("Service is shutting down.")
            raise CameraShutdownInProgressError("The camera is shutting down.")

        self.bind_notification_loop()

        if not isinstance(settings, StreamSettings):
            settings = StreamSettings(**settings)

        is_recording_start = (
            settings.video_record and not self.stream_settings.video_record
        )

        video_file = self.video_recorder.current_video_path

        is_recording_end = (
            self.stream_settings.video_record
            and not settings.video_record
            and video_file
        )

        should_restart = (
            self.camera_device_error or is_recording_start or not self.camera_run
        )
        _log.info("Updating stream settings, should camera restart %s", should_restart)
        self.stream_settings = settings
        if should_restart:
            await asyncio.to_thread(self.restart_camera)
        elif is_recording_end and video_file:
            await asyncio.to_thread(self.video_recorder.stop_recording_safe)
            await self.connection_manager.info(
                f"Post processing video {os.path.basename(video_file)}"
            )
            task = asyncio.create_task(
                VideoConverter.convert_video_async(video_file, video_file)
            )
            task.add_done_callback(
                lambda t: asyncio.create_task(self.notify_video_record_end(t))
            )

        await asyncio.to_thread(
            self.file_manager.save_settings,
            {"stream": self.stream_settings.model_dump()},
        )
        return self.stream_settings

    def _reset_camera_state(self) -> None:
        self.img = None
        self.stream_img = None
        self.current_frame_timestamp = None
        self.actual_fps = None
        self.frame_timestamps.clear()

    def _persist_camera_settings(self, settings: CameraSettings) -> None:
        try:
            self.file_manager.save_settings({"camera": settings.model_dump()})
        except Exception:
            _log.warning("Failed to persist camera settings", exc_info=True)

    @staticmethod
    def _release_cap_safe(cap: Optional[VideoCaptureABC]) -> None:
        """
        Safely releases the camera resource represented.
        """
        if cap is None:
            return
        try:
            cap.release()
        except Exception:
            _log.warning("Failed to release camera resource cleanly", exc_info=True)

    def _update_actual_fps(self, frame_timestamp: float, prev_fps: float) -> float:
        self.frame_timestamps.append(frame_timestamp)

        if len(self.frame_timestamps) < 5:
            return prev_fps

        time_window = self.frame_timestamps[-1] - self.frame_timestamps[0]
        if time_window < 0.5:
            return prev_fps

        actual_fps = calc_fps(self.frame_timestamps)
        if actual_fps is None:
            return prev_fps

        self.actual_fps = actual_fps
        if abs(actual_fps - prev_fps) > 1:
            _log.info("FPS: %s", actual_fps)
            return actual_fps
        return prev_fps

    def _prepare_video_recording_frame(self, frame: np.ndarray) -> np.ndarray:
        if not self.stream_settings.include_detection_overlay_in_media:
            return frame

        if not self.detection_service.detection_settings.active:
            return frame

        if hasattr(self.detection_service, "poll_detection_result"):
            self.detection_service.poll_detection_result()

        return prepare_detection_overlay_frame(
            frame=frame,
            detection_settings=self.detection_service.detection_settings,
            detection_state=self.detection_service.current_state,
            frame_timestamp=self.current_frame_timestamp,
        )

    def _camera_thread_func(self, cap: VideoCaptureABC) -> None:
        """
        Camera capture loop function.
        """
        prev_fps = 0.0
        capture_thread = threading.current_thread()
        self.frame_timestamps.clear()

        try:
            while not self.shutting_down and self.camera_run and self.cap is cap:
                frame_start_time = time.monotonic()
                ret, frame = cap.read()
                if not ret:
                    if self.shutting_down or not self.camera_run or self.cap is not cap:
                        break
                    self.camera_device_error = "Failed to read frame from the camera."
                    self._dispatch_camera_error(self.camera_device_error)
                    break

                if self.camera_device_error:
                    self._dispatch_camera_error(None)

                prev_fps = self._update_actual_fps(frame_start_time, prev_fps)
                self.current_frame_timestamp = time.time()

                enhance_mode = self.stream_settings.enhance_mode
                frame_enhancer = (
                    frame_enhancers.get(enhance_mode)
                    if enhance_mode is not None
                    else None
                )

                if not self.shutting_down and self.camera_run and self.cap is cap:
                    self.img = frame
                    try:
                        self.stream_img = (
                            frame if not frame_enhancer else frame_enhancer(frame)
                        )
                    except Exception as e:
                        self.camera_device_error = f"Failed to apply video effect: {e}"
                        self._dispatch_camera_error(self.camera_device_error)
                        break
                    if (
                        self.stream_settings.video_record
                        and self.stream_img is not None
                    ):
                        self.video_recorder.write_frame(
                            self._prepare_video_recording_frame(self.stream_img)
                        )

                    self._process_frame(frame)

        except KeyboardInterrupt:
            _log.info("Keyboard interrupt, stopping camera loop")
        except (
            ConnectionResetError,
            BrokenPipeError,
            EOFError,
            ConnectionError,
            ConnectionRefusedError,
        ) as e:
            _log.warning(
                "Stopped camera loop due to connection-related error: %s",
                type(e).__name__,
            )
        except Exception as exc:
            if not self.shutting_down and self.camera_run and self.cap is cap:
                self.camera_device_error = f"Camera capture failed: {exc}"
                self._dispatch_camera_error(self.camera_device_error)
            _log.error("Unhandled exception occurred in camera loop", exc_info=True)
        finally:
            if self.cap is cap:
                self._release_cap_safe(cap)
                self.cap = None
                self.camera_run = False
                self.video_recorder.stop_recording_safe()
                self._reset_camera_state()
            if self._capture_thread is capture_thread:
                self._capture_thread = None
            _log.info("Camera loop terminated and camera released.")

    def _process_frame(self, frame: "MatLike") -> None:
        """Handle frame detection."""
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
                pad_left,
                pad_top,
            ) = letterbox(
                frame,
                self.detection_service.detection_settings.img_size,
                self.detection_service.detection_settings.img_size,
            )

            frame_timestamp = self.current_frame_timestamp or time.time()
            self.current_frame_timestamp = frame_timestamp

            frame_data: DetectionFrameData = {
                "frame": resized_frame,
                "timestamp": frame_timestamp,
                "original_height": original_height,
                "original_width": original_width,
                "resized_height": resized_height,
                "resized_width": resized_width,
                "pad_left": pad_left,
                "pad_top": pad_top,
                "should_resize": False,
            }
            if not self.detection_service.shutting_down:
                self.detection_service.put_frame(frame_data)

    def _start_camera_locked(self) -> None:
        """
        Configures and starts the camera capture thread.

        Actions performed:
        - Releases any previously active camera device.
        - Sets up the camera device based on the current configuration.
        - Applies camera properties like resolution, FPS, and pixel format.
        - Starts a dedicated thread to run the capture loop.
        """

        _log.info("Starting camera.")
        if self.shutting_down:
            _log.warning("Service is shutting down.")
            return
        if (
            self.camera_run
            and self.cap is not None
            and self._capture_thread is not None
            and self._capture_thread.is_alive()
        ):
            _log.warning("Camera is already running.")
            return

        cap: Optional[VideoCaptureABC] = None
        previous_camera_settings = self.camera_settings.model_dump()

        try:
            self.video_recorder.stop_recording_safe()
            self._release_cap_safe(self.cap)
            self.cap = None
            self._capture_thread = None
            self._reset_camera_state()
            self.camera_run = True
            self._dispatch_camera_error(None)

            cap, props = self.video_device_adapter.setup_video_capture(
                self.camera_settings
            )
            _log.info(
                "Starting camera with props %s",
                props,
            )
            if self.stream_settings.video_record:
                _log.info(
                    "Starting camera recording"
                    if self.camera_settings.width and self.camera_settings.height
                    else f"Skipping camera recording due to missed "
                    f"width {self.camera_settings.width} or "
                    f"height {self.camera_settings.height}"
                )

            self.cap = cap
            self.camera_settings = props
            if self.camera_settings.model_dump() != previous_camera_settings:
                self._persist_camera_settings(self.camera_settings)
            if (
                self.stream_settings.video_record
                and self.camera_settings.width
                and self.camera_settings.height
            ):
                fps = self.camera_settings.fps or self.actual_fps
                self.video_recorder.start_recording(
                    width=self.camera_settings.width,
                    height=self.camera_settings.height,
                    fps=float(fps or 30),
                )
            self._capture_thread = threading.Thread(
                target=self._camera_thread_func,
                args=(cap,),
                daemon=True,
            )
            self._capture_thread.start()

        except (CameraNotFoundError, CameraDeviceError) as e:
            self.camera_run = False
            self.cap = None
            self._capture_thread = None
            self._reset_camera_state()
            self._release_cap_safe(cap)
            err_msg = str(e)
            self.camera_device_error = err_msg
            _log.error(err_msg)
            raise

        except Exception:
            self.camera_run = False
            self.cap = None
            self._capture_thread = None
            self._reset_camera_state()
            self._release_cap_safe(cap)
            _log.error("Unhandled exception", exc_info=True)
            raise

    def start_camera(self) -> None:
        with self._camera_operation_lock:
            self._start_camera_locked()

    async def start_camera_and_wait_for_stream_img(self) -> None:
        """
        Starts the camera asynchronously and ensures it is ready for streaming.
        """

        if not self.camera_run:
            self.bind_notification_loop()
            await asyncio.to_thread(self.start_camera)

        counter = 0

        while not self.camera_device_error:
            if self.stream_img is not None:
                break
            if counter <= 1:
                _log.debug("Waiting for stream img")
                counter += 1
            await asyncio.sleep(0.05)

        if self.camera_device_error:
            err = self.camera_device_error
            self.camera_device_error = None
            self.stop_camera()
            raise CameraDeviceError(err)

    def stop_camera(self) -> None:
        """
        Gracefully stops the camera capture thread and cleans up associated resources.
        """
        with self._camera_operation_lock:
            capture_thread = self._capture_thread
            cap = self.cap

            if (
                not self.camera_run
                and cap is None
                and (capture_thread is None or not capture_thread.is_alive())
            ):
                _log.info("Camera is not running.")
                return

            _log.info("Stopping camera and checking camera capture thread")

            self.camera_run = False
            self.cap = None
            self._capture_thread = None
            self.video_recorder.stop_recording_safe()
            self._reset_camera_state()
            self._release_cap_safe(cap)

            if (
                capture_thread is not None
                and capture_thread is not threading.current_thread()
                and capture_thread.is_alive()
            ):
                _log.info("Stopping camera capture thread")
                capture_thread.join()
                _log.info("Stopped camera capture thread")

    def restart_camera(self) -> None:
        """
        Restarts the camera by stopping and reinitializing it.
        """
        with self._camera_operation_lock:
            _log.info("Restarting camera")
            cam_running = self.camera_run or (
                self._capture_thread is not None and self._capture_thread.is_alive()
            )
            if cam_running or self.cap is not None:
                self.stop_camera()
            if not self.shutting_down:
                self._start_camera_locked()

    def shutdown(self) -> None:
        self.shutting_down = True
        self.stop_camera()
