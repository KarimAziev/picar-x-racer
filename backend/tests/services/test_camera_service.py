import logging
import threading
import time
import unittest
from typing import Any, Optional, cast
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
from app.adapters.video_device_adapter import VideoDeviceAdapter
from app.core.video_capture_abc import VideoCaptureABC
from app.schemas.camera import CameraSettings
from app.schemas.detection import DetectionSettings, OverlayStyle
from app.schemas.stream import StreamSettings
from app.services.camera.camera_service import CameraService
from app.services.connection_service import ConnectionService
from app.services.detection.detection_service import DetectionService
from app.services.domain.settings_service import SettingsService
from app.services.media.video_recorder_service import VideoRecorderService
from app.types.detection import DetectionQueueData


class DummyDetectionService:
    def __init__(self):
        self.detection_settings: Any = type(
            "Dummy", (), {"active": False, "img_size": 300}
        )()
        self.loading = False
        self.shutting_down = False
        self.detection_result: Optional[DetectionQueueData] = None
        self.poll_count = 0

    def put_frame(self, frame_data: np.ndarray):
        self.last_frame = frame_data

    def poll_detection_result(self) -> Optional[DetectionQueueData]:
        self.poll_count += 1
        return self.detection_result

    @property
    def current_state(self) -> DetectionQueueData:
        return self.detection_result or {
            "detection_result": [],
            "timestamp": time.time(),
        }


class DummyFileService:
    def __init__(self):
        self.settings = {
            "camera": {
                "device": None,
                "width": 640,
                "height": 480,
                "fps": 30,
                "pixel_format": "BGR",
                "media_type": "video/x-raw",
                "use_gstreamer": False,
            },
            "stream": {
                "format": ".jpg",
                "quality": 90,
                "enhance_mode": None,
                "video_record": False,
                "render_fps": True,
            },
        }
        self.saved_settings: list[dict[str, Any]] = []

    def save_settings(self, new_settings: dict[str, Any]):
        self.saved_settings.append(new_settings)
        self.settings = {**self.settings, **new_settings}
        return self.settings


class DummyConnectionService:
    def __init__(self):
        self.last_broadcast = None

    async def broadcast_json(self, data: Any, mode: str = "text"):
        logging.debug("broadcasting json data='%s' with mode='%s'", data, mode)
        pass

    async def info(self, message: str):
        logging.debug("info message='%s'", message)
        pass


class DummyVideoDeviceAdapter:
    def setup_video_capture(self, cam_settings: CameraSettings):
        dummy_cap = DummyVideoCapture()
        props = cam_settings.model_dump()
        props["width"] = 640
        props["height"] = 480
        props["fps"] = 30
        return dummy_cap, CameraSettings(**props)


class DummyVideoCapture:
    def __init__(self):
        self.is_opened = True

    def read(self):
        dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
        return True, dummy_image

    def release(self):
        self.is_opened = False


class DelayedStopVideoCapture:
    def __init__(self, delay: float = 0.2):
        self.is_opened = True
        self.delay = delay
        self.read_started = threading.Event()
        self.release_called = threading.Event()

    def read(self):
        self.read_started.set()
        while not self.release_called.is_set():
            time.sleep(0.01)
        time.sleep(self.delay)
        return False, np.empty((0, 0, 3), dtype=np.uint8)

    def release(self):
        self.is_opened = False
        self.release_called.set()


class ContinuousVideoCapture:
    def __init__(self):
        self.is_opened = True
        self.first_frame = threading.Event()
        self.read_count = 0

    def read(self):
        if not self.is_opened:
            return False, np.empty((0, 0, 3), dtype=np.uint8)
        self.read_count += 1
        self.first_frame.set()
        time.sleep(0.01)
        return True, np.zeros((480, 640, 3), dtype=np.uint8)

    def release(self):
        self.is_opened = False


class OneShotVideoCapture:
    def __init__(self):
        self.is_opened = True
        self.read_count = 0
        self.finished = threading.Event()

    def read(self):
        self.read_count += 1
        if self.read_count == 1:
            return True, np.zeros((480, 640, 3), dtype=np.uint8)
        self.finished.set()
        return False, np.empty((0, 0, 3), dtype=np.uint8)

    def release(self):
        self.is_opened = False


class SequenceVideoDeviceAdapter:
    def __init__(self, captures: list[Any]):
        self._captures = captures
        self.calls = 0

    def setup_video_capture(self, cam_settings: CameraSettings):
        cap = self._captures[self.calls]
        self.calls += 1
        props = cam_settings.model_dump()
        props["width"] = 640
        props["height"] = 480
        props["fps"] = 30
        return cap, CameraSettings(**props)


class ResolvedSettingsVideoDeviceAdapter:
    def setup_video_capture(self, cam_settings: CameraSettings):
        return (
            DummyVideoCapture(),
            CameraSettings(
                device="avfoundation:/camera-1",
                width=1280,
                height=720,
                fps=30,
                pixel_format="420v",
                media_type="video/x-raw",
                use_gstreamer=False,
            ),
        )


class DummyVideoRecorder:
    def __init__(self):
        self.current_video_path = None

    def start_recording(self, width, height, fps):
        self.recording = True
        self.width = width
        self.height = height
        self.fps = fps

    def write_frame(self, frame):
        self.last_frame_written = frame

    def stop_recording_safe(self):
        self.recording = False


class DummyLogger:
    name: str
    _app_logger_name = "test_px"

    def __init__(self, name: str, app_name: Optional[str] = None):
        if app_name:
            self.app_name = app_name
        self.name = name

    def info(self, *args, **kwargs):
        logging.debug("[info]: args=%s, kwargs=%s", args, kwargs)
        pass

    def warning(self, *args, **kwargs):
        logging.debug("[warning]: args=%s, kwargs=%s", args, kwargs)
        pass

    def error(self, *args, **kwargs):
        logging.debug("[error]: args=%s, kwargs=%s", args, kwargs)
        pass

    def debug(self, *args, **kwargs):
        logging.debug("[debug]: args=%s, kwargs=%s", args, kwargs)
        pass


def dummy_logger_patch(name: str):
    return DummyLogger(name)


def wait_until(predicate, timeout: float = 2.0, interval: float = 0.01):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


class TestCameraServiceAsync(unittest.IsolatedAsyncioTestCase):
    """Asysynchronous tests for async methods."""

    def setUp(self):

        self.detection_service = DummyDetectionService()
        self.settings_service = DummyFileService()
        self.connection_service = DummyConnectionService()
        self.video_device_adapter = DummyVideoDeviceAdapter()
        self.video_recorder = DummyVideoRecorder()

        patcher = patch("app.services.camera.camera_service.Logger", dummy_logger_patch)
        self.addCleanup(patcher.stop)
        patcher.start()

        self.camera_service = CameraService(
            detection_service=cast(DetectionService, self.detection_service),
            settings_service=cast(SettingsService, self.settings_service),
            connection_manager=cast(ConnectionService, self.connection_service),
            video_device_adapter=cast(VideoDeviceAdapter, self.video_device_adapter),
            video_recorder=cast(VideoRecorderService, self.video_recorder),
        )
        self.camera_service.shutting_down = False

        self.camera_service.stream_img = np.zeros((480, 640, 3), dtype=np.uint8)
        self.camera_service.current_frame_timestamp = time.time()
        self.camera_service.actual_fps = 25.0

    async def test_update_camera_settings_normal(self):
        """Patch restart_camera to avoid real thread spawning and camera opening."""
        with patch.object(self.camera_service, "restart_camera") as mock_restart:
            new_settings = CameraSettings(
                device="/dev/video0",
                width=800,
                height=600,
                fps=30,
                pixel_format="BGR",
                media_type="video/x-raw",
                use_gstreamer=False,
            )
            ret_settings = await self.camera_service.update_camera_settings(
                new_settings
            )
            self.assertEqual(ret_settings.width, 800)
            self.assertEqual(ret_settings.height, 600)
            mock_restart.assert_called_once()
            self.assertEqual(self.settings_service.saved_settings, [])

    async def test_update_stream_settings_restart(self):
        with patch.object(self.camera_service, "restart_camera") as mock_restart:
            new_stream_settings = StreamSettings(
                format=".jpg",
                quality=80,
                enhance_mode=None,
                video_record=True,
                render_fps=True,
            )
            ret = await self.camera_service.update_stream_settings(new_stream_settings)
            self.assertTrue(ret.video_record)
            mock_restart.assert_called_once()
            self.assertTrue(
                self.settings_service.saved_settings[-1]["stream"]["video_record"]
            )

    async def test_notify_camera_error_broadcasts_message(self):
        test_error = "Test camera error."

        with patch.object(
            self.camera_service.connection_manager,
            "broadcast_json",
            new_callable=AsyncMock,
        ) as mock_broadcast:
            await self.camera_service.notify_camera_error(test_error)
            calls = mock_broadcast.call_args_list

            error_call = next(
                (c for c in calls if c.args[0]["payload"] == test_error), None
            )
            self.assertIsNotNone(
                error_call,
                f"No broadcast_json call contained the payload {test_error}. Calls: {calls}",
            )

    async def test_start_camera_and_wait_for_stream_img(self):
        def fake_start_camera():
            self.camera_service.camera_run = True
            self.camera_service.stream_img = np.ones((480, 640, 3), dtype=np.uint8)
            self.camera_service.camera_device_error = None

        with patch.object(
            self.camera_service, "start_camera", side_effect=fake_start_camera
        ):
            self.camera_service.camera_device_error = None
            await self.camera_service.start_camera_and_wait_for_stream_img()
            self.assertIsNotNone(self.camera_service.stream_img)


class TestCameraServiceSync(unittest.TestCase):
    """Synchronous tests for non-async methods."""

    def setUp(self):

        self.detection_service = DummyDetectionService()
        self.settings_service = DummyFileService()
        self.connection_service = DummyConnectionService()
        self.video_device_adapter = DummyVideoDeviceAdapter()
        self.video_recorder = DummyVideoRecorder()

        patcher = patch("app.services.camera.camera_service.Logger", dummy_logger_patch)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.camera_service = CameraService(
            detection_service=cast(DetectionService, self.detection_service),
            settings_service=cast(SettingsService, self.settings_service),
            connection_manager=cast(ConnectionService, self.connection_service),
            video_device_adapter=cast(VideoDeviceAdapter, self.video_device_adapter),
            video_recorder=cast(VideoRecorderService, self.video_recorder),
        )
        self.camera_service.shutting_down = False

    def test_stop_camera_when_not_running(self):
        self.camera_service.camera_run = False
        self.camera_service.cap = cast(VideoCaptureABC, DummyVideoCapture())
        self.camera_service.stop_camera()
        self.assertIsNone(self.camera_service.cap)

    def test_dispatch_camera_error_uses_bound_loop(self):
        fake_loop = MagicMock()
        fake_loop.is_closed.return_value = False
        fake_loop.is_running.return_value = True
        fake_future = MagicMock()

        def submit(coro, loop):
            coro.close()
            return fake_future

        self.camera_service._notification_loop = fake_loop

        with patch(
            "app.services.camera.camera_service.asyncio.run_coroutine_threadsafe",
            side_effect=submit,
        ) as mock_submit:
            self.camera_service._dispatch_camera_error("boom")

        self.assertEqual(self.camera_service.camera_device_error, "boom")
        mock_submit.assert_called_once()
        fake_future.add_done_callback.assert_called_once()

    def test_restart_camera_calls_start_after_stop(self):
        self.camera_service.shutting_down = False
        self.camera_service.camera_run = True
        with patch.object(
            self.camera_service, "stop_camera", autospec=True
        ) as mock_stop, patch.object(
            self.camera_service, "_start_camera_locked", autospec=True
        ) as mock_start:
            self.camera_service.restart_camera()
            mock_stop.assert_called_once()
            mock_start.assert_called_once()

    def test_camera_thread_exit_marks_camera_stopped(self):
        one_shot_cap = OneShotVideoCapture()
        self.camera_service.video_device_adapter = cast(
            VideoDeviceAdapter, SequenceVideoDeviceAdapter([one_shot_cap])
        )

        self.camera_service.start_camera()

        self.assertTrue(wait_until(lambda: self.camera_service._capture_thread is None))
        self.assertFalse(self.camera_service.camera_run)
        self.assertIsNone(self.camera_service.cap)
        self.assertTrue(one_shot_cap.finished.is_set())
        self.assertEqual(
            self.camera_service.camera_device_error,
            "Failed to read frame from the camera.",
        )

    def test_concurrent_stop_and_start_keeps_new_capture_alive(self):
        old_cap = DelayedStopVideoCapture()
        new_cap = ContinuousVideoCapture()
        self.camera_service.video_device_adapter = cast(
            VideoDeviceAdapter, SequenceVideoDeviceAdapter([old_cap, new_cap])
        )

        self.camera_service.start_camera()
        self.assertTrue(old_cap.read_started.wait(timeout=1))

        stop_thread = threading.Thread(target=self.camera_service.stop_camera)
        start_thread = threading.Thread(target=self.camera_service.start_camera)

        stop_thread.start()
        self.assertTrue(old_cap.release_called.wait(timeout=1))
        start_thread.start()

        stop_thread.join(timeout=2)
        start_thread.join(timeout=2)

        self.assertFalse(stop_thread.is_alive())
        self.assertFalse(start_thread.is_alive())
        self.assertIs(self.camera_service.cap, new_cap)
        self.assertTrue(new_cap.first_frame.wait(timeout=1))
        self.assertTrue(self.camera_service.camera_run)
        self.assertTrue(new_cap.is_opened)

        self.camera_service.stop_camera()

    def test_start_camera_persists_resolved_camera_settings(self):
        self.camera_service.camera_settings = CameraSettings(
            device=None,
            width=640,
            height=480,
            fps=29,
            pixel_format="420v",
            media_type="video/x-raw",
            use_gstreamer=False,
        )
        self.camera_service.video_device_adapter = cast(
            VideoDeviceAdapter, ResolvedSettingsVideoDeviceAdapter()
        )

        self.camera_service.start_camera()
        self.camera_service.stop_camera()

        self.assertEqual(
            self.settings_service.saved_settings[-1]["camera"]["device"],
            "avfoundation:/camera-1",
        )
        self.assertEqual(
            self.settings_service.saved_settings[-1]["camera"]["fps"],
            30,
        )

    def test_video_recording_writes_detection_overlay_when_enabled(self):
        capture = OneShotVideoCapture()
        self.camera_service.video_device_adapter = cast(
            VideoDeviceAdapter, SequenceVideoDeviceAdapter([capture])
        )
        self.camera_service.stream_settings = StreamSettings(
            format=".jpg",
            quality=90,
            enhance_mode=None,
            video_record=True,
            render_fps=True,
            include_detection_overlay_in_media=True,
        )
        self.detection_service.detection_settings = DetectionSettings(
            model="yolo11n.pt",
            confidence=0.4,
            active=True,
            img_size=640,
            labels=None,
            overlay_draw_threshold=60.0,
            overlay_style=OverlayStyle.BOX,
        )
        self.detection_service.detection_result = {
            "detection_result": [
                {
                    "bbox": [10, 10, 40, 40],
                    "label": "person",
                    "confidence": 0.95,
                }
            ],
            "timestamp": time.time(),
        }

        self.camera_service.start_camera()

        self.assertTrue(wait_until(lambda: self.camera_service._capture_thread is None))
        written = self.video_recorder.last_frame_written
        self.assertEqual(tuple(written[10, 10]), (191, 255, 0))
        self.assertGreater(self.detection_service.poll_count, 0)

    def test_video_recording_skips_detection_overlay_when_disabled(self):
        capture = OneShotVideoCapture()
        self.camera_service.video_device_adapter = cast(
            VideoDeviceAdapter, SequenceVideoDeviceAdapter([capture])
        )
        self.camera_service.stream_settings = StreamSettings(
            format=".jpg",
            quality=90,
            enhance_mode=None,
            video_record=True,
            render_fps=True,
            include_detection_overlay_in_media=False,
        )
        self.detection_service.detection_settings = DetectionSettings(
            model="yolo11n.pt",
            confidence=0.4,
            active=True,
            img_size=640,
            labels=None,
            overlay_draw_threshold=60.0,
            overlay_style=OverlayStyle.BOX,
        )
        self.detection_service.detection_result = {
            "detection_result": [
                {
                    "bbox": [10, 10, 40, 40],
                    "label": "person",
                    "confidence": 0.95,
                }
            ],
            "timestamp": time.time(),
        }

        self.camera_service.start_camera()

        self.assertTrue(wait_until(lambda: self.camera_service._capture_thread is None))
        written = self.video_recorder.last_frame_written
        self.assertTrue(
            np.array_equal(written, np.zeros((480, 640, 3), dtype=np.uint8))
        )
        self.assertEqual(self.detection_service.poll_count, 0)


if __name__ == "__main__":
    unittest.main()
