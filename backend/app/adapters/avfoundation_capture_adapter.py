import os
import select
import shutil
import subprocess
import threading
import time
from collections import deque
from typing import IO, TYPE_CHECKING, Deque, Optional, Tuple

import cv2
import numpy as np
from app.core.logger import Logger
from app.core.video_capture_abc import VideoCaptureABC
from app.exceptions.camera import CameraDeviceError
from app.schemas.camera import CameraSettings
from app.util.device import release_video_capture_safe
from app.adapters.avfoundation_camera_controls import AVFoundationCameraControls

if TYPE_CHECKING:
    from app.services.camera.avfoundation_service import AVFoundationService
    from cv2.typing import MatLike

_log = Logger(name=__name__)


class AVFoundationCaptureAdapter(VideoCaptureABC):
    def __init__(
        self,
        device: str,
        camera_settings: CameraSettings,
        service: "AVFoundationService",
    ) -> None:
        super().__init__(service=service)
        self.service = service
        self._controls: Optional[AVFoundationCameraControls] = None
        self._stderr_lines: Deque[str] = deque(maxlen=20)
        self._stderr_thread: Optional[threading.Thread] = None
        self._process_lock = threading.Lock()
        self._cap: Optional[cv2.VideoCapture] = None
        self._process: Optional[subprocess.Popen[bytes]] = None
        self._released = False
        self._buffered_frame: Optional[np.ndarray] = None
        self._frame_byte_size = 0
        self._width = 0
        self._height = 0
        self._settings: CameraSettings
        input_name, resolved_settings = self.service.resolve_capture_config(
            device, camera_settings
        )
        try:
            cap, frame, updated_settings = self._start_opencv_capture(
                device, resolved_settings
            )
            with self._process_lock:
                self._cap = cap
                self._released = False
                self._buffered_frame = frame
            self._settings = updated_settings
        except CameraDeviceError as opencv_error:
            if camera_settings.controls.requested:
                raise CameraDeviceError(
                    "Exposure and focus controls require OpenCV AVFoundation capture; FFmpeg fallback cannot apply them."
                ) from opencv_error
            _log.warning(
                "OpenCV AVFoundation capture failed, falling back to FFmpeg: %s",
                opencv_error,
            )
            self._process, self._settings = self._start_process(
                input_name, resolved_settings
            )
        try:
            if camera_settings.controls.requested:
                self._controls = self.service.camera_controls(device)
                self._controls.apply(camera_settings.controls)
                self._buffered_frame = None
        except Exception:
            self.release()
            raise

    @property
    def settings(self) -> CameraSettings:
        return self._settings

    @staticmethod
    def _empty_frame() -> np.ndarray:
        return np.empty((0, 0), dtype=np.uint8)

    @staticmethod
    def _escape_input_name(name: str) -> str:
        return name.replace("\\", "\\\\").replace(":", "\\:")

    def _start_opencv_capture(
        self, device: str, settings: CameraSettings
    ) -> Tuple[cv2.VideoCapture, np.ndarray, CameraSettings]:
        device_index = self.service.resolve_capture_index(device)
        cap = cv2.VideoCapture(device_index, cv2.CAP_AVFOUNDATION)
        if not cap.isOpened():
            release_video_capture_safe(cap)
            raise CameraDeviceError("Failed to open macOS camera with OpenCV.")

        if settings.width is not None:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, settings.width)
        if settings.height is not None:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.height)
        if settings.fps is not None:
            cap.set(cv2.CAP_PROP_FPS, float(settings.fps))

        ok, frame = cap.read()
        if not ok or frame is None or frame.size == 0:
            release_video_capture_safe(cap)
            raise CameraDeviceError("Failed to read frame from macOS camera.")

        height, width = frame.shape[:2]
        updated_settings = {
            **settings.model_dump(),
            "device": settings.device or device,
            "width": int(width),
            "height": int(height),
            "fps": float(settings.fps or 30.0),
            "use_gstreamer": False,
        }
        return cap, frame.copy(), CameraSettings(**updated_settings)

    @staticmethod
    def _build_command(
        ffmpeg_bin: str,
        input_name: str,
        width: int,
        height: int,
        fps: float,
        prefer_bgr0: bool,
    ) -> list[str]:
        command = [
            ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-fflags",
            "nobuffer",
            "-f",
            "avfoundation",
        ]
        if prefer_bgr0:
            command.extend(["-pixel_format", "bgr0"])
        command.extend(
            [
                "-framerate",
                f"{fps:g}",
                "-video_size",
                f"{width}x{height}",
                "-i",
                f"{AVFoundationCaptureAdapter._escape_input_name(input_name)}:none",
                "-an",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "bgr24",
                "pipe:1",
            ]
        )
        return command

    @staticmethod
    def _read_exact(
        pipe: Optional[IO[bytes]],
        byte_count: int,
        timeout: Optional[float],
        process: subprocess.Popen[bytes],
    ) -> Optional[bytes]:
        if pipe is None or byte_count <= 0:
            return None

        try:
            fd = pipe.fileno()
        except (OSError, ValueError):
            return None
        chunks: list[bytes] = []
        remaining = byte_count
        deadline = None if timeout is None else time.monotonic() + timeout

        while remaining > 0:
            if process.poll() is not None:
                wait_timeout = 0.0
            elif deadline is None:
                wait_timeout = None
            else:
                wait_timeout = max(0.0, deadline - time.monotonic())
                if wait_timeout == 0.0:
                    return None

            try:
                ready, _, _ = select.select([fd], [], [], wait_timeout)
            except (OSError, ValueError):
                return None
            if not ready:
                return None

            try:
                chunk = os.read(fd, remaining)
            except OSError:
                return None
            if not chunk:
                return None

            chunks.append(chunk)
            remaining -= len(chunk)

        return b"".join(chunks)

    def _bytes_to_frame(self, frame_bytes: bytes) -> np.ndarray:
        return (
            np.frombuffer(frame_bytes, dtype=np.uint8)
            .reshape((self._height, self._width, 3))
            .copy()
        )

    def _collect_process_error(self, process: subprocess.Popen[bytes]) -> str:
        stderr_output = b""
        if process.stderr is not None:
            try:
                stderr_output = process.stderr.read() or b""
            except Exception:
                stderr_output = b""

        stderr_text = stderr_output.decode("utf-8", errors="replace").strip()
        if stderr_text:
            return stderr_text
        if self._stderr_lines:
            return "\n".join(self._stderr_lines)
        return "Unknown FFmpeg error."

    @staticmethod
    def _stop_process(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        try:
            process.terminate()
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    @staticmethod
    def _close_pipe(pipe: Optional[IO[bytes]]) -> None:
        if pipe is None:
            return
        try:
            pipe.close()
        except Exception:
            pass

    def _start_stderr_reader(self, process: subprocess.Popen[bytes]) -> None:
        stderr_pipe = process.stderr
        if stderr_pipe is None:
            return

        def reader() -> None:
            try:
                for raw_line in iter(stderr_pipe.readline, b""):
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if line:
                        self._stderr_lines.append(line)
            except Exception:
                pass

        self._stderr_thread = threading.Thread(target=reader, daemon=True)
        self._stderr_thread.start()

    def _attempt_process_start(
        self,
        command: list[str],
        width: int,
        height: int,
    ) -> Tuple[Optional[subprocess.Popen[bytes]], Optional[np.ndarray], Optional[str]]:
        frame_byte_size = width * height * 3
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=max(frame_byte_size * 4, 1),
        )
        frame_bytes = self._read_exact(
            process.stdout,
            frame_byte_size,
            timeout=5.0,
            process=process,
        )
        if frame_bytes is None:
            self._stop_process(process)
            return None, None, self._collect_process_error(process)

        self._width = width
        self._height = height
        self._frame_byte_size = frame_byte_size
        return process, self._bytes_to_frame(frame_bytes), None

    def _start_process(
        self, input_name: str, settings: CameraSettings
    ) -> Tuple[subprocess.Popen[bytes], CameraSettings]:
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin is None:
            raise CameraDeviceError(
                "The macOS camera backend requires 'ffmpeg' in PATH."
            )

        width = int(settings.width or 0)
        height = int(settings.height or 0)
        fps = float(settings.fps or 30.0)
        if width <= 0 or height <= 0:
            raise CameraDeviceError(
                "Invalid camera dimensions for AVFoundation capture"
            )

        errors: list[str] = []
        for prefer_bgr0 in (True, False):
            command = self._build_command(
                ffmpeg_bin,
                input_name=input_name,
                width=width,
                height=height,
                fps=fps,
                prefer_bgr0=prefer_bgr0,
            )
            _log.info("Starting AVFoundation FFmpeg command: %s", command)
            process, frame, error = self._attempt_process_start(command, width, height)
            if process is not None and frame is not None:
                with self._process_lock:
                    self._process = process
                    self._released = False
                    self._buffered_frame = frame
                self._start_stderr_reader(process)
                return process, settings
            if error:
                errors.append(error)

        error_text = " | ".join(dict.fromkeys(errors))
        raise CameraDeviceError(
            "Failed to start macOS AVFoundation capture."
            + (f" {error_text}" if error_text else "")
        )

    def read(self) -> Tuple[bool, "MatLike"]:
        with self._process_lock:
            if self._buffered_frame is not None:
                frame = self._buffered_frame
                self._buffered_frame = None
                return True, frame
            cap = self._cap
            process = self._process
            released = self._released

        if released:
            return False, self._empty_frame()

        if cap is not None:
            with self._process_lock:
                if self._released or self._cap is not cap:
                    return False, self._empty_frame()
                ok, frame = cap.read()
            if not ok or frame is None:
                return False, self._empty_frame()
            return True, frame.copy()

        if process is None or process.stdout is None:
            return False, self._empty_frame()

        frame_bytes = self._read_exact(
            process.stdout,
            self._frame_byte_size,
            timeout=2.0,
            process=process,
        )
        if frame_bytes is None:
            with self._process_lock:
                released_during_read = self._released or self._process is not process
            if not released_during_read and process.poll() is not None:
                _log.error(
                    "AVFoundation FFmpeg capture stopped: %s",
                    self._collect_process_error(process),
                )
            return False, self._empty_frame()

        return True, self._bytes_to_frame(frame_bytes)

    def release(self) -> None:
        try:
            if self._controls is not None:
                self._controls.close()
        finally:
            self._release_capture()

    def _release_capture(self) -> None:
        with self._process_lock:
            cap = self._cap
            self._cap = None
            process = self._process
            self._process = None
            self._released = True
            self._buffered_frame = None
        release_video_capture_safe(cap)
        if process is not None:
            self._stop_process(process)
            self._close_pipe(process.stdout)
            self._close_pipe(process.stderr)
            if self._stderr_thread is not None and self._stderr_thread.is_alive():
                self._stderr_thread.join(timeout=1)
