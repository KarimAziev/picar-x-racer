import unittest
from concurrent.futures import CancelledError
from types import ModuleType
from unittest.mock import MagicMock, call, patch

import numpy as np
from app.adapters.picamera_capture_adapter import PicameraCaptureAdapter
from app.exceptions.camera import CameraDeviceError
from app.schemas.camera import CameraSettings
from app.services.camera.picamera2_service import PicameraService


class TestPicameraCaptureAdapter(unittest.TestCase):
    def setUp(self):
        self.camera = MagicMock()
        self.camera.create_video_configuration.return_value = {
            "main": {"format": "XBGR8888"},
            "controls": {"FrameDurationLimits": (33333, 33333)},
        }
        self.frame = np.zeros((4, 4, 4), dtype=np.uint8)
        self.camera.capture_array.return_value.get_result.return_value = self.frame
        self.camera_class = MagicMock(return_value=self.camera)
        self.camera_class.global_camera_info.return_value = [
            {"Id": "/camera", "Num": 2}
        ]
        module = ModuleType("picamera2")
        module.Picamera2 = self.camera_class  # type: ignore[attr-defined]
        self.modules = patch.dict(
            "sys.modules", {"picamera2": module, "picamera2.formats": MagicMock()}
        )
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def create_adapter(self):
        return PicameraCaptureAdapter(
            "/camera", CameraSettings(fps=30), PicameraService()
        )

    def test_initial_timeout_closes_camera_and_identifies_device(self):
        self.camera.capture_array.return_value.get_result.side_effect = TimeoutError()
        with self.assertRaisesRegex(CameraDeviceError, r"/camera.*5.*seconds"):
            self.create_adapter()
        self.camera.capture_array.assert_called_once_with(wait=False)
        self.camera.capture_array.return_value.get_result.assert_called_once_with(
            timeout=5.0
        )
        self.camera.cancel_all_and_flush.assert_called_once()
        self.camera.close.assert_called_once()

    def test_configuration_failure_closes_camera(self):
        self.camera.configure.side_effect = RuntimeError("invalid configuration")
        with self.assertRaisesRegex(CameraDeviceError, "invalid configuration"):
            self.create_adapter()
        self.camera.close.assert_called_once()

    def test_read_timeout_reports_device_error(self):
        adapter = self.create_adapter()
        self.camera.capture_array.return_value.get_result.side_effect = TimeoutError()
        with self.assertRaisesRegex(CameraDeviceError, r"/camera.*5.*seconds"):
            adapter.read()
        adapter.release()

    def test_release_cancels_pending_capture_before_close_and_is_idempotent(self):
        adapter = self.create_adapter()
        self.camera.reset_mock()
        adapter.release()
        adapter.release()
        self.assertEqual(
            self.camera.mock_calls, [call.cancel_all_and_flush(), call.close()]
        )

    def test_release_attempts_close_if_cancel_fails(self):
        adapter = self.create_adapter()
        self.camera.cancel_all_and_flush.side_effect = RuntimeError("flush failed")
        adapter.release()
        self.camera.close.assert_called_once()

    def test_uses_reported_camera_number(self):
        adapter = self.create_adapter()
        self.camera_class.assert_called_once_with(2)
        adapter.release()

    def test_photo_uses_native_still_configuration(self):
        self.camera.create_still_configuration.return_value = {
            "main": {"format": "RGB888"},
            "controls": {},
        }
        self.camera.capture_array.return_value.get_result.return_value = np.zeros(
            (6, 8, 3), dtype=np.uint8
        )
        adapter = PicameraCaptureAdapter(
            "/camera", CameraSettings(width=8, height=6), PicameraService(), still=True
        )
        self.camera.create_still_configuration.assert_called_once_with(
            main={"size": (8, 6)}
        )
        self.camera.create_video_configuration.assert_not_called()
        self.assertEqual(adapter.read()[1].shape, (6, 8, 3))
        adapter.release()

    def test_manual_controls_are_set_before_start(self):
        self.camera.camera_controls = {
            "AeEnable": (False, True, True),
            "ExposureTime": (100, 100000, 10000),
            "AfMode": (0, 2, 0),
            "LensPosition": (0.0, 10.0, 1.0),
        }
        settings = CameraSettings.model_validate(
            {
                "fps": 30,
                "controls": {
                    "exposure_mode": "manual",
                    "exposure_time_us": 10000,
                    "focus_mode": "manual",
                    "focus_position": 2.5,
                },
            }
        )
        adapter = PicameraCaptureAdapter("/camera", settings, PicameraService())
        self.camera.set_controls.assert_called_once_with(
            {"AeEnable": False, "ExposureTime": 10000, "AfMode": 0, "LensPosition": 2.5}
        )
        calls = self.camera.mock_calls
        self.assertLess(
            calls.index(
                call.set_controls(
                    {
                        "AeEnable": False,
                        "ExposureTime": 10000,
                        "AfMode": 0,
                        "LensPosition": 2.5,
                    }
                )
            ),
            calls.index(call.start()),
        )
        adapter.release()

    def test_unsupported_focus_closes_camera_without_starting(self):
        self.camera.camera_controls = {"AeEnable": (False, True, True)}
        settings = CameraSettings.model_validate({"controls": {"focus_mode": "auto"}})
        with self.assertRaisesRegex(CameraDeviceError, "Focus"):
            PicameraCaptureAdapter("/camera", settings, PicameraService())
        self.camera.start.assert_not_called()
        self.camera.close.assert_called_once()

    def test_manual_still_exposure_allows_variable_frame_duration(self):
        self.camera.create_still_configuration.return_value = {
            "main": {"format": "RGB888"},
            "controls": {"FrameDurationLimits": (100, 1000000)},
        }
        self.camera.camera_controls = {
            "AeEnable": (False, True, True),
            "ExposureTime": (100, 1000000, 10000),
        }
        settings = CameraSettings.model_validate(
            {"controls": {"exposure_mode": "manual", "exposure_time_us": 50000}}
        )
        adapter = PicameraCaptureAdapter(
            "/camera", settings, PicameraService(), still=True
        )
        self.assertIsNone(adapter.settings.fps)
        self.camera.set_controls.assert_called_once_with(
            {"AeEnable": False, "ExposureTime": 50000}
        )
        adapter.release()

    def test_release_cancellation_ends_read_without_device_error(self):
        adapter = self.create_adapter()
        adapter.release()
        self.camera.capture_array.return_value.get_result.side_effect = CancelledError()
        success, _ = adapter.read()
        self.assertFalse(success)
