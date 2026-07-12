import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

from app.adapters.picarx_adapter import PicarxAdapter
from app.schemas.robot.config import HardwareConfig
from app.services.control.calibration_service import CalibrationService
from pydantic import ValidationError
from robot_hat import MotorService, SingleMotorService


class TestMotorConfiguration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config_path = Path(__file__).resolve().parents[4] / "config.json"
        with config_path.open() as config_file:
            cls.config_data = json.load(config_file)

    def test_hardware_config_accepts_one_or_two_motors(self):
        one_motor = {**self.config_data, "motors": self.config_data["motors"][:1]}

        self.assertEqual(len(HardwareConfig(**one_motor).motors), 1)
        self.assertEqual(len(HardwareConfig(**self.config_data).motors), 2)

    def test_hardware_config_rejects_invalid_motor_counts(self):
        for motors in ([], self.config_data["motors"] * 2):
            with self.subTest(count=len(motors)), self.assertRaises(ValidationError):
                HardwareConfig(**{**self.config_data, "motors": motors})

    def test_adapter_selects_single_motor_service(self):
        adapter = PicarxAdapter.__new__(PicarxAdapter)
        adapter.config = cast(Any, SimpleNamespace(motors=[object()]))
        adapter.motors = [MagicMock()]

        adapter._init_motor_controller()

        self.assertIsInstance(adapter.motor_controller, SingleMotorService)

    def test_adapter_selects_dual_motor_service(self):
        adapter = PicarxAdapter.__new__(PicarxAdapter)
        adapter.config = cast(Any, SimpleNamespace(motors=[object(), object()]))
        adapter.motors = [MagicMock(), MagicMock()]

        adapter._init_motor_controller()

        self.assertIsInstance(adapter.motor_controller, MotorService)

    def test_adapter_does_not_change_service_mode_after_partial_init(self):
        adapter = PicarxAdapter.__new__(PicarxAdapter)
        adapter.config = cast(Any, SimpleNamespace(motors=[object(), object()]))
        adapter.motors = [MagicMock()]

        adapter._init_motor_controller()

        self.assertIsNone(adapter.motor_controller)


class TestMotorCalibration(unittest.TestCase):
    def setUp(self):
        self.motors = [MagicMock(direction=1), MagicMock(direction=-1)]
        for motor in self.motors:
            motor.update_calibration_direction.side_effect = (
                lambda value, target=motor: setattr(target, "direction", value)
            )
        picarx = SimpleNamespace(
            motors=self.motors,
            motor_controller=MagicMock(),
            steering_servo=None,
            cam_tilt_servo=None,
            cam_pan_servo=None,
        )
        self.service = CalibrationService(cast(Any, picarx), MagicMock())

    def test_updates_motor_calibration_by_index(self):
        result = self.service.update_motor_direction({"index": 1, "value": 1})

        self.motors[1].update_calibration_direction.assert_called_once_with(1)
        self.assertEqual(
            result["motors"],
            [{"calibration_direction": 1}, {"calibration_direction": 1}],
        )

    def test_rejects_unknown_motor_index(self):
        with self.assertRaisesRegex(ValueError, "Motor 3 is not configured"):
            self.service.update_motor_direction({"index": 2, "value": 1})

    def test_rejects_invalid_motor_direction(self):
        with self.assertRaisesRegex(ValueError, "either 1 or -1"):
            self.service.update_motor_direction({"index": 0, "value": 0})


if __name__ == "__main__":
    unittest.main()
