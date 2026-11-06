import unittest
from pathlib import Path
from threading import Event, RLock
from unittest.mock import MagicMock, patch

from app.adapters.picarx_adapter import PicarxAdapter
from app.schemas.robot.config import HardwareConfig
from app.schemas.robot.servo_tuning import ServoTuningRequest
from app.services.control.settings_service import SettingsService
from pydantic import ValidationError


class TestServoTuning(unittest.TestCase):
    def setUp(self) -> None:
        self.config = HardwareConfig.model_validate_json(
            (Path(__file__).resolve().parents[4] / "config.json").read_text()
        )
        self.adapter = PicarxAdapter.__new__(PicarxAdapter)
        self.adapter.config = self.config
        self.adapter._hardware_lock = RLock()
        self.adapter._shutdown_requested = Event()
        self.adapter.motor_controller = None
        self.adapter.cam_pan_servo = None
        self.adapter.cam_tilt_servo = None
        self.servo = MagicMock()
        self.servo.current_angle = 5
        self.servo.calibration_offset = 2
        self.adapter.steering_servo = self.servo
        self.manager = MagicMock()
        self.manager.load_data.return_value = self.config.model_dump(mode="json")
        self.service = SettingsService(self.adapter, self.manager)

    def request(self, **settings: int) -> ServoTuningRequest:
        return ServoTuningRequest.model_validate(
            {"servo": "steering_servo", "settings": settings, "angle": 40}
        )

    def test_preview_applies_before_movement_and_does_not_persist(self) -> None:
        replacement = MagicMock()
        replacement.calibration_offset = 2
        with patch.object(self.adapter, "_make_servo", return_value=replacement):
            result = self.service.preview_servo_tuning(self.request(max_angle=45))
        self.assertEqual(result.max_angle, 45)
        replacement.set_angle.assert_called_once_with(40)
        self.servo.close.assert_called_once()
        self.manager.update.assert_not_called()
        self.assertEqual(
            self.service.get_current_settings().steering_servo.max_angle, 45
        )
        self.assertNotEqual(
            self.service.get_saved_settings().steering_servo.max_angle, 45
        )

    def test_reverse_preview_is_applied_and_included_in_saved_tuning(self) -> None:
        original_reverse = self.service.get_saved_settings().steering_servo.reverse
        replacement = MagicMock()
        replacement.calibration_offset = 2
        request = ServoTuningRequest.model_validate(
            {
                "servo": "steering_servo",
                "settings": {"reverse": not original_reverse},
                "angle": -10,
            }
        )
        with patch.object(
            self.adapter, "_make_servo", return_value=replacement
        ) as make_servo:
            result = self.service.preview_servo_tuning(request)
        self.assertEqual(result.reverse, not original_reverse)
        self.assertEqual(make_servo.call_args.args[0].reverse, not original_reverse)
        replacement.set_angle.assert_called_once_with(-10)
        self.assertEqual(
            self.service.get_current_settings().steering_servo.reverse,
            not original_reverse,
        )
        self.assertEqual(
            self.service.get_saved_settings().steering_servo.reverse, original_reverse
        )
        self.manager.update.assert_not_called()

    def test_invalid_ranges_do_not_touch_hardware(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.preview_servo_tuning(self.request(min_angle=80, max_angle=10))
        self.servo.close.assert_not_called()
        self.manager.update.assert_not_called()

    def test_failed_preview_restores_configuration_and_servo(self) -> None:
        previous = self.adapter.config.steering_servo.model_copy(deep=True)
        restored = MagicMock()
        with patch.object(
            self.adapter,
            "_make_servo",
            side_effect=[RuntimeError("PWM failed"), restored],
        ):
            with self.assertRaisesRegex(RuntimeError, "PWM failed"):
                self.service.preview_servo_tuning(self.request(max_angle=45))
        self.assertEqual(self.adapter.config.steering_servo, previous)
        self.assertIs(self.adapter.steering_servo, restored)
        self.manager.update.assert_not_called()

    def test_rejects_wiring_changes_and_nonfinite_angles(self) -> None:
        for request in (
            {"servo": "steering_servo", "settings": {"pin": 5}, "angle": 0},
            {"servo": "steering_servo", "settings": {}, "angle": float("nan")},
        ):
            with self.assertRaises(ValidationError):
                ServoTuningRequest.model_validate(request)


class TestServoTuningMotion(unittest.IsolatedAsyncioTestCase):
    async def test_tuning_pauses_motion_and_reports_physical_steering(self) -> None:
        from unittest.mock import AsyncMock
        from app.services.control.car_service import CarService
        from app.services.autonomy.messages import RobotMode

        car = CarService.__new__(CarService)
        car._shutting_down = False
        car.servo_tuning_active = False
        car.px = MagicMock()
        car.px.calibration_active = False
        car.px.state = {"speed": 0, "direction": 0, "steering_servo_angle": 40}
        car.motion_control_service = MagicMock()
        car.motion_control_service.mode = RobotMode.MANUAL
        car.motion_control_service.running = True
        car.motion_control_service.set_mode = AsyncMock()
        car.motion_control_service.stop = AsyncMock()

        await car.start_servo_tuning()
        car.motion_control_service.set_mode.assert_awaited_once_with(RobotMode.DISARMED)
        car.motion_control_service.stop.assert_awaited_once()
        self.assertEqual(car._current_drive_state(), (0, 0, 40))
        await car.handle_set_servo_dir_angle(45)
        car.px.set_dir_servo_angle.assert_called_once_with(45)
        await car.stop_servo_tuning()
        car.motion_control_service.start.assert_called_once()
        self.assertFalse(car.servo_tuning_active)

    async def test_offset_adjustments_broadcast_updated_servo_positions(self) -> None:
        from unittest.mock import AsyncMock
        from app.services.control.car_service import CarService

        car = CarService.__new__(CarService)
        car._shutting_down = False
        car.px = MagicMock()
        car.px.calibration_active = False
        car.calibration = MagicMock()
        car.motion_control_service = None
        car.connection_manager = MagicMock()
        with patch.object(
            car, "broadcast_calibration", new_callable=AsyncMock
        ) as offsets, patch.object(car, "broadcast", new_callable=AsyncMock) as gauges:
            await car.process_action("updateCamPanCali", 2.5, MagicMock())
            offsets.assert_awaited_once()
            gauges.assert_awaited_once()
