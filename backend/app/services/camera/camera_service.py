import asyncio
import collections
import os
import threading
import time
from typing import TYPE_CHECKING, Optional, Union

import numpy as np
from app.config.video_enhancers import frame_enhancers
from app.core.event_emitter import EventEmitter
from app.core.logger import Logger
from app.core.singleton_meta import SingletonMeta
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
from app.util.video_utils import calc_fps, letterbox

if TYPE_CHECKING:
    from app.adapters.video_device_adapter import VideoDeviceAdapter
    from app.services.connection_service import ConnectionService
    from app.services.detection.detection_service import DetectionService
    from app.services.domain.settings_service import SettingsService
    from app.services.media.video_recorder_service import VideoRecorderService
    from cv2.typing import MatLike


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
        settings_service: "SettingsService",
        connection_manager: "ConnectionService",
        video_device_adapter: "VideoDeviceAdapter",
        video_recorder: "VideoRecorderService",
    ):
        """
        Initializes the `CameraService` singleton instance.
        """
        self.logger = Logger(name=__name__)
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
        self.camera_device_error: Optional[str] = None
        self.camera_loading: bool = False
        self.shutting_down = False

        self.emitter = EventEmitter()
        self.emitter.on("frame_error", self.notify_camera_error)

    async def notify_camera_error(self, error: Optional[str]):
        self.camera_device_error = error

        await self.connection_manager.broadcast_json(
            {"type": "camera_error", "payload": error}
        )

    async def notify_video_record_end(self, task: asyncio.Task[Union[str, None]]):
        try:
            video_file = await task
            self.logger.info("video_file result='%s'", video_file)
            if video_file:
                self.logger.info(f"Post-processing successful: {video_file}")
                rel_name = os.path.basename(video_file)
                await self.connection_manager.broadcast_json(
                    {"type": "video_record_end", "payload": rel_name}
                )
            else:
                self.logger.error("Video processing failed")
                await self.connection_manager.broadcast_json(
                    {"type": "video_record_error", "payload": "Video processing failed"}
                )
        except Exception:
            self.logger.error(
                "Unexpected error in video processing callback:", exc_info=True
            )
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
            self.logger.warning("Service is shutting down.")
            raise CameraShutdownInProgressError("The camera is shutting down.")

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
            self.logger.warning("Service is shutting down.")
            raise CameraShutdownInProgressError("The camera is shutting down.")

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
        self.logger.info(
            "Updating stream settings, should camera restart %s", should_restart
        )
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

        return self.stream_settings

    def _release_cap_safe(self) -> None:
        """
        Safely releases the camera resource represented.
        """
        if self.cap:
            self.cap.release()
        self.cap = None

    def _camera_thread_func(self) -> None:
        """
        Camera capture loop function.
        """
        prev_fps = 0.0

        self.frame_timestamps: collections.deque[float] = collections.deque(maxlen=30)
        try:
            while not self.shutting_down and self.camera_run and self.cap:
                frame_start_time = time.time()
                ret, frame = self.cap.read()
                if not ret:
                    self.camera_device_error = "Failed to read frame from the camera."
                    self.emitter.emit("frame_error", self.camera_device_error)
                    break

                else:

                    if self.camera_device_error:
                        self.emitter.emit("frame_error", None)

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

                if not self.shutting_down:
                    self.img = frame
                    try:
                        self.stream_img = (
                            frame if not frame_enhancer else frame_enhancer(frame)
                        )
                    except Exception as e:
                        self.camera_device_error = f"Failed to apply video effect: {e}"
                        self.emitter.emit("frame_error", self.camera_device_error)
                        break
                    if (
                        self.stream_settings.video_record
                        and self.stream_img is not None
                    ):
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

            self.current_frame_timestamp = time.time()

            frame_data: DetectionFrameData = {
                "frame": resized_frame,
                "timestamp": self.current_frame_timestamp,
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

    def start_camera(self) -> None:
        """
        Configures and starts the camera capture thread.

        Actions performed:
        - Releases any previously active camera device.
        - Sets up the camera device based on the current configuration.
        - Applies camera properties like resolution, FPS, and pixel format.
        - Starts a dedicated thread to run the capture loop.
        """

        self.logger.info("Starting camera.")
        if self.shutting_down:
            self.logger.warning("Service is shutting down.")
        if self.camera_run:
            self.logger.warning("Camera is already running.")
            return
        self.camera_run = True
        self.emitter.emit("frame_error", None)
        try:
            self.video_recorder.stop_recording_safe()
            self._release_cap_safe()
            cap, props = self.video_device_adapter.setup_video_capture(
                self.camera_settings
            )
            self.logger.info(
                "Camera props %s, video record is %s",
                props,
                self.stream_settings.video_record,
            )
            self.cap = cap
            self.camera_settings = props
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
            self.capture_thread = threading.Thread(
                target=self._camera_thread_func, daemon=True
            )
            self.capture_thread.start()
            self.camera_device_error = None

        except (CameraNotFoundError, CameraDeviceError) as e:
            self.stop_camera()
            err_msg = str(e)
            self.camera_device_error = err_msg
            self.stream_img = None
            self.logger.error(err_msg)
            raise

        except Exception:
            self.stop_camera()
            self.camera_run = False
            self.logger.error("Unhandled exception", exc_info=True)
            raise

    async def start_camera_and_wait_for_stream_img(self):
        """
        Starts the camera asynchronously and ensures it is ready for streaming.
        """

        if not self.camera_run:
            await asyncio.to_thread(self.start_camera)

        counter = 0

        while not self.camera_device_error:
            if self.stream_img is not None:
                break
            if counter <= 1:
                self.logger.debug("waiting for stream img")
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
        if not self.camera_run:
            self.logger.info("Camera is not running.")
            self._release_cap_safe()
            return

        self.logger.info("Stopping camera")

        self.camera_run = False

        self.logger.info("Checking camera capture thread")

        if hasattr(self, "capture_thread") and self.capture_thread.is_alive():
            self.logger.info("Stopping camera capture thread")
            self.capture_thread.join()
            self.logger.info("Stopped camera capture thread")

    def restart_camera(self) -> None:
        """
        Restarts the camera by stopping and reinitializing it.
        """
        self.logger.info("Restarting camera")
        cam_running = self.camera_run
        if cam_running:
            self.stop_camera()
        if not self.shutting_down:
            self.start_camera()

    def shutdown(self) -> None:
        self.shutting_down = True
        self.stop_camera()
