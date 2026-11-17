import asyncio
import threading
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
from app.exceptions.camera import (
    CameraDeviceError,
    CameraBusyError,
    CameraShutdownInProgressError,
)
from app.schemas.photo import PhotoCameraSettings, PhotoPreset, PhotoSettings
from app.schemas.camera_controls import (
    CameraControls,
    CameraControlCapabilities,
    ControlRange,
)
from app.services.camera.camera_service import CameraService
from pydantic import ValidationError


class TestPhotoPresets(unittest.TestCase):
    def test_requires_explicit_device_and_positive_dimensions(self):
        for camera in ({}, {"device": "camera", "width": 0, "height": 480}):
            with self.assertRaises(ValidationError):
                PhotoPreset.model_validate(
                    {"id": "test", "name": "Test", "camera": camera}
                )

    def test_rejects_duplicate_ids_and_unknown_selection(self):
        preset = PhotoPreset(
            id="test",
            name="Test",
            camera=PhotoCameraSettings(device="camera", width=8, height=6),
        )
        with self.assertRaises(ValidationError):
            PhotoSettings(presets=[preset, preset])
        with self.assertRaises(ValidationError):
            PhotoSettings(selected_preset_id="missing")


class TestPhotoCapture(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = MagicMock()
        self.settings.settings = {
            "camera": {"device": "stream", "width": 4, "height": 3}
        }
        self.adapter = MagicMock()
        self.recorder = MagicMock()
        self.recorder.current_video_path = None
        self.connection = MagicMock()
        self.connection.broadcast_json = AsyncMock()
        self.detection = MagicMock()
        self.service = CameraService(
            self.detection, self.settings, self.connection, self.adapter, self.recorder
        )
        self.service.camera_run = True
        self.service.img = np.zeros((3, 4, 3), dtype=np.uint8)
        self.service.stream_img = self.service.img
        self.preset = PhotoPreset(
            id="high",
            name="High resolution",
            camera=PhotoCameraSettings(device="photo", width=8, height=6),
            settle_seconds=0,
        )
        self.cap = MagicMock()
        self.cap.read.return_value = (True, np.ones((6, 8, 3), dtype=np.uint8))
        self.adapter.setup_photo_capture.return_value = (self.cap, self.preset.camera)
        self.adapter.validate_photo_settings.return_value = None
        self.stop_patch = patch.object(self.service, "stop_camera")
        self.start_patch = patch.object(self.service, "_start_camera_locked")
        self.stop = self.stop_patch.start()
        self.start = self.start_patch.start()
        self.addCleanup(self.stop_patch.stop)
        self.addCleanup(self.start_patch.stop)

    async def test_captures_owned_pixels_and_restores_without_persisting(self):
        original = self.service.camera_settings.model_copy(deep=True)
        frame = await self.service.capture_preset_photo(self.preset)
        self.assertEqual(frame.shape, (6, 8, 3))
        self.cap.read.return_value[1][:] = 0
        self.assertEqual(int(frame.min()), 1)
        self.assertEqual(self.service.camera_settings, original)
        self.start.assert_called_once_with(persist_settings=False)
        self.cap.release.assert_called_once()
        self.settings.save_settings.assert_not_called()
        self.assertFalse(self.service.photo_capturing)

    async def test_restores_after_open_failure(self):
        self.adapter.setup_photo_capture.side_effect = CameraDeviceError("open failed")
        with self.assertRaisesRegex(CameraDeviceError, "open failed"):
            await self.service.capture_preset_photo(self.preset)
        self.start.assert_called_once_with(persist_settings=False)
        self.assertFalse(self.service.photo_capturing)

    async def test_photo_controls_are_independent_and_stream_controls_are_restored(
        self,
    ):
        stream_controls = CameraControls(exposure_mode="auto", focus_mode="auto")
        self.service.camera_settings.controls = stream_controls
        self.preset.camera.controls = CameraControls(
            exposure_mode="manual",
            exposure_time_us=10000,
            focus_mode="manual",
            focus_position=2,
        )
        self.adapter.control_capabilities.return_value = CameraControlCapabilities(
            exposure_modes=["auto", "manual"],
            exposure_time_us=ControlRange(min=100, max=100000, step=100, unit="µs"),
            focus_modes=["auto", "manual"],
            focus_position=ControlRange(min=0, max=10, unit="dioptres"),
        )
        await self.service.capture_preset_photo(self.preset)
        self.adapter.setup_photo_capture.assert_called_once_with(self.preset.camera)
        self.assertEqual(self.service.camera_settings.controls, stream_controls)
        self.start.assert_called_once_with(persist_settings=False)

    async def test_unsupported_photo_controls_do_not_interrupt_stream(self):
        self.preset.camera.controls = CameraControls(focus_mode="auto")
        self.adapter.control_capabilities.return_value = CameraControlCapabilities()
        with self.assertRaisesRegex(CameraDeviceError, "Focus"):
            await self.service.capture_preset_photo(self.preset)
        self.stop.assert_not_called()
        self.adapter.setup_photo_capture.assert_not_called()

    async def test_failed_stream_control_update_restores_previous_settings(self):
        original = self.service.camera_settings.model_copy(deep=True)
        requested = original.model_copy(deep=True)
        requested.controls = CameraControls(focus_mode="auto")
        self.adapter.control_capabilities.return_value = CameraControlCapabilities(
            focus_modes=["auto"]
        )
        with patch.object(
            self.service,
            "restart_camera",
            side_effect=[CameraDeviceError("Rejected"), None],
        ) as restart:
            with self.assertRaisesRegex(CameraDeviceError, "Rejected"):
                await self.service.update_camera_settings(requested)
        self.assertEqual(restart.call_count, 2)
        self.assertEqual(self.service.camera_settings, original)

    async def test_rejects_wrong_resolution_and_restores(self):
        self.cap.read.return_value = (True, np.zeros((3, 4, 3), dtype=np.uint8))
        with self.assertRaisesRegex(CameraDeviceError, "resolution"):
            await self.service.capture_preset_photo(self.preset)
        self.cap.release.assert_called_once()
        self.start.assert_called_once()

    async def test_rejects_recording_before_touching_camera(self):
        self.service.stream_settings.video_record = True
        with self.assertRaises(CameraBusyError):
            await self.service.capture_preset_photo(self.preset)
        self.stop.assert_not_called()
        self.adapter.setup_photo_capture.assert_not_called()

    async def test_does_not_start_previously_stopped_camera(self):
        self.service.camera_run = False
        await self.service.capture_preset_photo(self.preset)
        self.start.assert_not_called()

    async def test_can_capture_after_recording_has_stopped(self):
        self.recorder.current_video_path = "/videos/completed.mp4"
        self.service.stream_settings.video_record = False
        frame = await self.service.capture_preset_photo(self.preset)
        self.assertEqual(frame.shape, (6, 8, 3))

    async def test_reports_restore_failure(self):
        self.start.side_effect = CameraDeviceError("stream unavailable")
        with self.assertRaisesRegex(CameraDeviceError, "restore"):
            await self.service.capture_preset_photo(self.preset)
        self.assertIn("restore", self.service.camera_device_error or "")
        self.assertFalse(self.service.photo_capturing)

    async def test_reports_wrong_dimensions_after_restoration(self):
        original = self.service.camera_settings.model_copy(deep=True)

        def start(*, persist_settings: bool):
            self.service.img = np.zeros((2, 2, 3), dtype=np.uint8)

        self.start.side_effect = start
        with self.assertRaisesRegex(CameraDeviceError, "restore"):
            await self.service.capture_preset_photo(self.preset)
        self.assertEqual(self.service.camera_settings, original)

    async def test_cancellation_waits_for_restoration(self):
        entered = threading.Event()
        finish = threading.Event()

        def read():
            entered.set()
            finish.wait(2)
            return True, np.ones((6, 8, 3), dtype=np.uint8)

        self.cap.read.side_effect = read
        task = asyncio.create_task(self.service.capture_preset_photo(self.preset))
        await asyncio.to_thread(entered.wait, 2)
        task.cancel()
        await asyncio.sleep(0.01)
        self.assertFalse(task.done())
        finish.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.start.assert_called_once()
        self.assertFalse(self.service.photo_capturing)

    async def test_shutdown_does_not_restart_stream(self):
        def read():
            self.service.shutting_down = True
            return True, np.ones((6, 8, 3), dtype=np.uint8)

        self.cap.read.side_effect = read
        with self.assertRaises(CameraShutdownInProgressError):
            await self.service.capture_preset_photo(self.preset)
        self.start.assert_not_called()

    async def test_serializes_camera_settings_until_restore_finishes(self):
        entered = threading.Event()
        finish = threading.Event()

        def read():
            entered.set()
            finish.wait(2)
            return True, np.ones((6, 8, 3), dtype=np.uint8)

        self.cap.read.side_effect = read
        capture = asyncio.create_task(self.service.capture_preset_photo(self.preset))
        self.assertTrue(await asyncio.to_thread(entered.wait, 2))
        with patch.object(
            self.service, "_update_camera_settings", new_callable=AsyncMock
        ) as update:
            change = asyncio.create_task(
                self.service.update_camera_settings(self.service.camera_settings)
            )
            await asyncio.sleep(0.01)
            update.assert_not_awaited()
            finish.set()
            await capture
            await change
            update.assert_awaited_once()

    async def test_real_capture_thread_restarts_with_original_dimensions(self):
        from tests.services.test_camera_service import ContinuousVideoCapture

        self.stop_patch.stop()
        self.start_patch.stop()
        self.service.camera_run = False
        self.service.img = None
        self.service.stream_img = None
        stream_settings = self.service.camera_settings.model_copy(
            update={"width": 640, "height": 480}
        )
        self.service.camera_settings = stream_settings
        self.service.detection_service.detection_settings.active = True
        self.service.detection_service.detection_settings.img_size = 320
        self.service.detection_service.loading = False
        self.service.detection_service.shutting_down = False
        detected = threading.Event()
        self.detection.put_frame.side_effect = lambda frame: detected.set()
        stream = ContinuousVideoCapture()
        restored = ContinuousVideoCapture()
        self.adapter.setup_video_capture.side_effect = [
            (stream, stream_settings),
            (restored, stream_settings),
        ]
        try:
            await asyncio.to_thread(self.service.start_camera)
            self.assertTrue(await asyncio.to_thread(stream.first_frame.wait, 2))
            frame = await self.service.capture_preset_photo(self.preset)
            self.assertEqual(frame.shape, (6, 8, 3))
            self.assertFalse(stream.is_opened)
            self.assertTrue(restored.is_opened)
            self.assertTrue(self.service.camera_run)
            self.assertIsNotNone(self.service.stream_img)
            if self.service.stream_img is not None:
                self.assertEqual(self.service.stream_img.shape, (480, 640, 3))
            self.assertEqual(self.service.camera_settings, stream_settings)
            self.settings.save_settings.assert_not_called()
            self.assertTrue(await asyncio.to_thread(detected.wait, 2))
            self.detection.put_frame.assert_called()
            for call in self.detection.put_frame.call_args_list:
                self.assertEqual(call.args[0]["original_width"], 640)
        finally:
            await asyncio.to_thread(self.service.stop_camera)
