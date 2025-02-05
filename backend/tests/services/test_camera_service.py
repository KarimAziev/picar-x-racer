import logging
import struct
import time
import unittest
from typing import Any, Optional, cast
from unittest.mock import AsyncMock, patch

import numpy as np
from app.adapters.capture_adapter import VideoCaptureAdapter
from app.adapters.video_device_adapter import VideoDeviceAdapater
from app.exceptions.camera import CameraShutdownInProgressError
from app.schemas.camera import CameraSettings
from app.schemas.stream import StreamSettings
from app.services.camera_service import CameraService
from app.services.connection_service import ConnectionService
from app.services.detection_service import DetectionService
from app.services.file_service import FileService
from app.services.video_recorder import VideoRecorder


class DummyDetectionService:
    def __init__(self):
        self.detection_settings = type(
            "Dummy", (), {"active": False, "img_size": 300}
        )()
        self.loading = False
        self.shutting_down = False

    def put_frame(self, frame_data: np.ndarray):
        self.last_frame = frame_data


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


class DummyConnectionService:
    def __init__(self):
        self.last_broadcast = None

    async def broadcast_json(self, data: Any, mode: str = "text"):
        logging.debug("broadcasting json data='%s' with mode='%s'", data, mode)
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


class DummyVideoRecorder:
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


class TestCameraServiceAsync(unittest.IsolatedAsyncioTestCase):
    """Asysynchronous tests for async methods."""

    def setUp(self):
        from app.core.singleton_meta import SingletonMeta

        SingletonMeta._instances.pop(CameraService, None)

        self.detection_service = cast(DetectionService, DummyDetectionService())
        self.file_service = cast(FileService, DummyFileService())
        self.connection_service = cast(ConnectionService, DummyConnectionService())
        self.video_device_adapter = cast(VideoDeviceAdapater, DummyVideoDeviceAdapter())
        self.video_recorder = cast(VideoRecorder, DummyVideoRecorder())

        patcher = patch("app.services.camera_service.Logger", dummy_logger_patch)
        self.addCleanup(patcher.stop)
        patcher.start()

        self.camera_service = CameraService(
            detection_service=self.detection_service,
            file_manager=self.file_service,
            connection_manager=self.connection_service,
            video_device_adapter=self.video_device_adapter,
            video_recorder=self.video_recorder,
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

    async def test_generate_frame_returns_correct_bytes(self):
        """Test generate_frame returns a bytes object when therea are no errors and not shutting down."""
        self.camera_service.shutting_down = False
        frame_bytes = self.camera_service.generate_frame()
        self.assertIsInstance(frame_bytes, bytes)
        frame_bytes = cast(bytes, frame_bytes)
        # Unpack first 16 bytes as two doubles.
        timestamp, fps = struct.unpack("dd", frame_bytes[:16])
        self.assertIsInstance(timestamp, float)
        self.assertEqual(fps, 25.0)
        self.assertGreater(len(frame_bytes), 16)  # more than header bytes

    async def test_generate_frame_raises_shutdown_error(self):
        self.camera_service.shutting_down = True
        with self.assertRaises(CameraShutdownInProgressError):
            self.camera_service.generate_frame()

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
        from app.core.singleton_meta import SingletonMeta

        SingletonMeta._instances.pop(CameraService, None)

        self.detection_service = cast(DetectionService, DummyDetectionService())
        self.file_service = cast(FileService, DummyFileService())
        self.connection_service = cast(ConnectionService, DummyConnectionService())
        self.video_device_adapter = cast(VideoDeviceAdapater, DummyVideoDeviceAdapter())
        self.video_recorder = cast(VideoRecorder, DummyVideoRecorder())

        patcher = patch("app.services.camera_service.Logger", dummy_logger_patch)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.camera_service = CameraService(
            detection_service=self.detection_service,
            file_manager=self.file_service,
            connection_manager=self.connection_service,
            video_device_adapter=self.video_device_adapter,
            video_recorder=self.video_recorder,
        )
        self.camera_service.shutting_down = False

    def test_stop_camera_when_not_running(self):
        self.camera_service.camera_run = False
        self.camera_service.cap = cast(VideoCaptureAdapter, DummyVideoCapture())
        self.camera_service.stop_camera()
        self.assertIsNone(self.camera_service.cap)

    def test_restart_camera_calls_start_after_stop(self):
        self.camera_service.shutting_down = False
        self.camera_service.camera_run = True
        with patch.object(
            self.camera_service, "stop_camera", autospec=True
        ) as mock_stop, patch.object(
            self.camera_service, "start_camera", autospec=True
        ) as mock_start:
            self.camera_service.restart_camera()
            mock_stop.assert_called_once()
            mock_start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
