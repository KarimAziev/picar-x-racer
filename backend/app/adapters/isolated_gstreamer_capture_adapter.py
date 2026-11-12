"""Run native libcamera/GStreamer capture outside the web server process."""

import multiprocessing as mp
import signal
import threading
import time
from multiprocessing.connection import Connection
from typing import Any, Optional, Tuple

import numpy as np
from app.core.video_capture_abc import VideoCaptureABC
from app.exceptions.camera import CameraDeviceError, CameraFrameTimeout
from app.schemas.camera import CameraSettings
from app.services.camera.gstreamer_service import GStreamerService


def _capture_worker(
    connection: Connection, device: str, settings: dict[str, Any]
) -> None:
    from app.adapters.gstreamer_capture_adapter import GStreamerCaptureAdapter

    capture: Optional[GStreamerCaptureAdapter] = None
    try:
        capture = GStreamerCaptureAdapter(
            device, CameraSettings(**settings), GStreamerService()
        )
        deadline = time.monotonic() + 5.0
        while True:
            try:
                ok, frame = capture.read()
                if not ok:
                    raise CameraDeviceError(
                        "GStreamer stopped before producing a frame"
                    )
                break
            except CameraFrameTimeout:
                if time.monotonic() >= deadline:
                    raise CameraDeviceError(
                        "GStreamer: no camera frame received for 5 seconds"
                    )
        connection.send(("ready", (capture.settings.model_dump(), frame)))
        while connection.recv() == "read":
            try:
                ok, frame = capture.read()
                connection.send(("frame", frame) if ok else ("end", None))
            except CameraFrameTimeout as err:
                connection.send(("timeout", str(err)))
    except (EOFError, BrokenPipeError):
        pass
    except Exception as err:
        try:
            connection.send(("error", str(err)))
        except (EOFError, BrokenPipeError):
            pass
    finally:
        if capture is not None:
            capture.release()
        connection.close()


class IsolatedGStreamerCaptureAdapter(VideoCaptureABC):
    """Translate worker failures into camera errors with bounded waits and cleanup."""

    START_TIMEOUT_SECONDS = 8.0
    READ_TIMEOUT_SECONDS = 2.0

    def __init__(
        self, device: str, camera_settings: CameraSettings, service: GStreamerService
    ):
        super().__init__(service)
        # Validate before launching native code, including persisted settings.
        service.setup_pipeline(
            device,
            width=camera_settings.width,
            height=camera_settings.height,
            fps=camera_settings.fps,
            pixel_format=camera_settings.pixel_format,
            media_type=camera_settings.media_type,
        )
        self.device = device
        self._closed = threading.Event()
        self._io_lock = threading.Lock()
        self._first_frame: Optional[np.ndarray] = None
        context = mp.get_context("spawn")
        self._connection, child_connection = context.Pipe()
        self._process = context.Process(
            target=_capture_worker,
            args=(child_connection, device, camera_settings.model_dump()),
            name="libcamera_gstreamer_capture",
            daemon=True,
        )
        try:
            self._process.start()
            child_connection.close()
            kind, payload = self._receive(self.START_TIMEOUT_SECONDS)
            if kind != "ready":
                raise CameraDeviceError(f"GStreamer {device}: {payload}")
            settings, self._first_frame = payload
            self._settings = CameraSettings(**settings)
        except Exception:
            child_connection.close()
            self.release()
            raise

    @property
    def settings(self) -> CameraSettings:
        return self._settings

    def _worker_error(self) -> CameraDeviceError:
        self._process.join(0.2)
        code = self._process.exitcode
        reason = (
            signal.Signals(-code).name
            if code is not None and code < 0
            else f"exit code {code}"
        )
        return CameraDeviceError(
            f"GStreamer {self.device}: camera worker exited ({reason}). "
            "The native camera backend stopped; see the service log for libcamera diagnostics."
        )

    def _receive(self, timeout: float) -> tuple[str, Any]:
        deadline = time.monotonic() + timeout
        while not self._closed.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CameraDeviceError(
                    f"GStreamer {self.device}: camera worker timed out after {timeout:g} seconds"
                )
            try:
                if self._connection.poll(min(0.1, remaining)):
                    return self._connection.recv()
            except (EOFError, OSError):
                raise self._worker_error()
            if self._process.exitcode is not None:
                raise self._worker_error()
        return "end", None

    def read(self) -> Tuple[bool, np.ndarray]:
        with self._io_lock:
            if self._closed.is_set():
                return False, np.empty((0, 0), dtype=np.uint8)
            if self._first_frame is not None:
                frame, self._first_frame = self._first_frame, None
                return True, frame
            try:
                self._connection.send("read")
            except (BrokenPipeError, OSError):
                raise self._worker_error()
            kind, payload = self._receive(self.READ_TIMEOUT_SECONDS)
            if kind == "frame":
                return True, payload
            if kind == "timeout":
                raise CameraFrameTimeout(payload)
            if kind == "end":
                return False, np.empty((0, 0), dtype=np.uint8)
            raise CameraDeviceError(f"GStreamer {self.device}: {payload}")

    def release(self) -> None:
        self._closed.set()
        with self._io_lock:
            if self._connection.closed:
                return
            try:
                if self._process.pid is not None:
                    if self._process.is_alive():
                        try:
                            self._connection.send("stop")
                        except (BrokenPipeError, OSError):
                            pass
                    self._process.join(1.0)
                    if self._process.is_alive():
                        self._process.terminate()
                        self._process.join(1.0)
                    if self._process.is_alive():
                        self._process.kill()
                        self._process.join(1.0)
                    if not self._process.is_alive():
                        self._process.close()
            finally:
                self._connection.close()
                self._first_frame = None
