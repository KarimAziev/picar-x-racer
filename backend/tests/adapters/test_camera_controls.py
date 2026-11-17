import unittest

from app.schemas.camera import CameraSettings
from app.schemas.camera_controls import (
    CameraControls,
    CameraControlCapabilities,
    ControlRange,
)
from app.exceptions.camera import CameraDeviceError
from pydantic import ValidationError


class TestCameraControls(unittest.TestCase):
    def test_defaults_preserve_camera_controls(self):
        self.assertFalse(CameraSettings().controls.requested)

    def test_manual_modes_require_values_and_auto_rejects_manual_values(self):
        for data in [
            {"exposure_mode": "manual"},
            {"focus_mode": "manual"},
            {"exposure_mode": "auto", "exposure_time_us": 1000},
            {"focus_position": 2},
            {"focus_mode": "manual", "focus_position": float("nan")},
        ]:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                CameraControls.model_validate(data)

    def test_device_ranges_and_steps_are_enforced(self):
        caps = CameraControlCapabilities(
            exposure_modes=["auto", "manual"],
            exposure_time_us=ControlRange(min=100, max=10000, step=100, unit="µs"),
        )
        caps.validate_controls(
            CameraControls(exposure_mode="manual", exposure_time_us=1000)
        )
        for value in [50, 150, 11000]:
            with self.subTest(value=value), self.assertRaises(CameraDeviceError):
                caps.validate_controls(
                    CameraControls(exposure_mode="manual", exposure_time_us=value)
                )
        with self.assertRaises(CameraDeviceError):
            caps.validate_controls(CameraControls(focus_mode="auto"))

    def test_exposure_must_fit_frame_interval(self):
        with self.assertRaises(ValidationError):
            CameraSettings.model_validate(
                {
                    "fps": 30,
                    "controls": {"exposure_mode": "manual", "exposure_time_us": 50000},
                }
            )


class TestV4L2Controls(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        import v4l2
        from app.adapters.v4l2_camera_controls import (
            EXPOSURE_MODE,
            EXPOSURE_TIME,
            FOCUS_MODE,
            FOCUS_POSITION,
        )

        self.v4l2 = v4l2
        self.ids = (EXPOSURE_MODE, EXPOSURE_TIME, FOCUS_MODE, FOCUS_POSITION)
        self.values = dict(zip(self.ids, [1, 80, 0, 20]))
        self.ranges = dict(
            zip(self.ids, [(0, 3, 1), (1, 1000, 1), (0, 1, 1), (0, 255, 5)])
        )
        self.writes = []
        self.fail_id = None
        for target, kwargs in [
            ("os.open", {"return_value": 7}),
            ("os.close", {}),
            ("fcntl.ioctl", {"side_effect": self.ioctl}),
        ]:
            patcher = patch(f"app.adapters.v4l2_camera_controls.{target}", **kwargs)
            mock = patcher.start()
            if target == "os.close":
                self.close_mock = mock
            self.addCleanup(patcher.stop)

    def ioctl(self, fd, op, control):
        if op == self.v4l2.VIDIOC_QUERYCTRL:
            if control.id not in self.ranges:
                raise OSError("Unsupported")
            control.minimum, control.maximum, control.step = self.ranges[control.id]
        elif op == self.v4l2.VIDIOC_QUERYMENU:
            if control.index not in (1, 3):
                raise OSError("Unsupported menu entry")
        elif op == self.v4l2.VIDIOC_G_CTRL:
            control.value = self.values[control.id]
        elif op == self.v4l2.VIDIOC_S_CTRL:
            if control.id == self.fail_id:
                self.fail_id = None
                raise OSError("Device rejected control")
            self.writes.append((control.id, control.value))
            self.values[control.id] = control.value
        return 0

    def test_units_order_and_original_manual_values_are_restored(self):
        from app.adapters.v4l2_camera_controls import V4L2CameraControls

        original = dict(self.values)
        controls = V4L2CameraControls("/dev/video0")
        controls.apply(
            CameraControls(
                exposure_mode="manual",
                exposure_time_us=15000,
                focus_mode="manual",
                focus_position=35,
            )
        )
        self.assertEqual(self.writes, list(zip(self.ids, [1, 150, 0, 35])))
        controls.close()
        self.assertEqual(self.values, original)
        controls.close()
        self.close_mock.assert_called_once_with(7)

    def test_partial_failure_can_restore_both_controls(self):
        from app.adapters.v4l2_camera_controls import V4L2CameraControls

        original = dict(self.values)
        controls = V4L2CameraControls("/dev/video0")
        self.fail_id = self.ids[3]
        with self.assertRaises(CameraDeviceError):
            controls.apply(
                CameraControls(
                    exposure_mode="auto", focus_mode="manual", focus_position=35
                )
            )
        controls.close()
        self.assertEqual(self.values, original)

    def test_unsupported_control_is_rejected_without_writes(self):
        from app.adapters.v4l2_camera_controls import V4L2CameraControls

        self.ranges.pop(self.ids[2])
        self.ranges.pop(self.ids[3])
        controls = V4L2CameraControls("/dev/video0")
        with self.assertRaises(CameraDeviceError):
            controls.apply(CameraControls(focus_mode="manual", focus_position=5))
        self.assertEqual(self.writes, [])
        controls.close()


class TestAVFoundationControls(unittest.TestCase):
    def setUp(self):
        from unittest.mock import MagicMock
        from app.adapters.avfoundation_camera_controls import AVFoundationCameraControls

        self.device = MagicMock()
        self.av = MagicMock()
        self.av.AVCaptureExposureModeCustom = 3
        self.av.AVCaptureExposureModeContinuousAutoExposure = 2
        self.av.AVCaptureFocusModeLocked = 0
        self.av.AVCaptureFocusModeContinuousAutoFocus = 2
        self.av.AVCaptureISOCurrent = 0
        self.cm = MagicMock()
        self.cm.CMTimeGetSeconds.side_effect = float
        self.cm.CMTimeMake.side_effect = lambda value, scale: value / scale
        self.device.activeFormat.return_value.minExposureDuration.return_value = 0.001
        self.device.activeFormat.return_value.maxExposureDuration.return_value = 0.1
        self.device.lockForConfiguration_.return_value = (True, None)
        self.device.exposureMode.return_value = 3
        self.device.exposureDuration.return_value = 0.02
        self.device.ISO.return_value = 100
        self.device.focusMode.return_value = 0
        self.device.lensPosition.return_value = 0.6
        self.controls = AVFoundationCameraControls(self.device, (self.av, self.cm))

    def test_applies_native_units_and_restores_original_manual_values(self):
        self.controls.apply(
            CameraControls(
                exposure_mode="manual",
                exposure_time_us=10000,
                focus_mode="manual",
                focus_position=0.3,
            )
        )
        self.device.setExposureModeCustomWithDuration_ISO_completionHandler_.assert_called_with(
            0.01, 0, None
        )
        self.device.setFocusModeLockedWithLensPosition_completionHandler_.assert_called_with(
            0.3, None
        )
        self.controls.close()
        self.device.setExposureModeCustomWithDuration_ISO_completionHandler_.assert_called_with(
            0.02, 100, None
        )
        self.device.setFocusModeLockedWithLensPosition_completionHandler_.assert_called_with(
            0.6, None
        )
        self.assertEqual(self.device.unlockForConfiguration.call_count, 2)

    def test_fixed_camera_exposes_no_controls(self):
        self.device.isExposureModeSupported_.return_value = False
        self.device.isFocusModeSupported_.return_value = False
        self.assertEqual(self.controls.capabilities.exposure_modes, [])
        self.assertEqual(self.controls.capabilities.focus_modes, [])
        with self.assertRaises(CameraDeviceError):
            self.controls.apply(CameraControls(exposure_mode="auto"))
        self.device.lockForConfiguration_.assert_not_called()

    def test_configuration_lock_failure_does_not_write(self):
        self.device.lockForConfiguration_.return_value = (False, "Busy")
        with self.assertRaisesRegex(CameraDeviceError, "Busy"):
            self.controls.apply(CameraControls(focus_mode="auto"))
        self.device.setFocusMode_.assert_not_called()
