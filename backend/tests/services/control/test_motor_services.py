import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, call, patch

from app.adapters.picarx_adapter import PicarxAdapter
from app.schemas.robot.config import HardwareConfig
from app.schemas.robot.pwm import PWMDriverConfig
from app.services.control.calibration_service import CalibrationService
from app.services.control.settings_service import SettingsService
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
        self.settings_service = MagicMock()
        self.service = CalibrationService(cast(Any, picarx), self.settings_service)

    def test_updates_motor_calibration_by_index(self):
        result = self.service.update_motor_direction({"index": 1, "value": 1})

        self.motors[1].update_calibration_direction.assert_called_once_with(1)
        self.motors[1].stop.assert_called_once_with()
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

    def test_reverse_motor_stops_before_changing_direction(self):
        result = self.service.reverse_motor(0)

        self.motors[0].stop.assert_called_once_with()
        self.motors[0].update_calibration_direction.assert_called_once_with(-1)
        self.assertEqual(
            self.motors[0].method_calls[:2],
            [call.stop(), call.update_calibration_direction(-1)],
        )
        self.assertEqual(result["motors"][0]["calibration_direction"], -1)

    def test_reset_stops_controller_before_resetting_calibration(self):
        controller = cast(MagicMock, self.service.px.motor_controller)

        self.service.reset_calibration()

        controller.stop_all.assert_called_once_with()
        controller.reset_calibration.assert_called_once_with()
        self.assertEqual(
            controller.method_calls[:2],
            [call.stop_all(), call.reset_calibration()],
        )

    def test_save_calibration_persists_the_current_runtime_settings(self):
        current = MagicMock()
        saved = MagicMock()
        saved.model_dump.return_value = {"saved": True}
        self.settings_service.get_current_settings.return_value = current
        self.settings_service.save_settings.return_value = saved

        result = self.service.save_calibration()

        self.settings_service.save_settings.assert_called_once_with(current)
        saved.model_dump.assert_called_once_with(mode="json")
        self.assertEqual(result, {"saved": True})


class TestMotorCalibrationSettings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config_path = Path(__file__).resolve().parents[4] / "config.json"
        with config_path.open() as config_file:
            cls.config_data = json.load(config_file)

    def test_current_settings_use_runtime_direction_for_enabled_motors(self):
        config_manager = MagicMock()
        config_manager.load_data.return_value = self.config_data
        active_configs = [
            motor for motor in self.config_data["motors"] if motor.get("enabled", True)
        ]
        runtime_directions = [
            -1 if index == 0 else 1 for index in range(len(active_configs))
        ]
        picarx = SimpleNamespace(
            steering_servo=None,
            cam_tilt_servo=None,
            cam_pan_servo=None,
            motor_controller=object(),
            motors=[
                SimpleNamespace(direction=direction) for direction in runtime_directions
            ],
        )
        service = SettingsService(cast(Any, picarx), config_manager)

        settings = service.get_current_settings()

        self.assertEqual(
            [motor.calibration_direction for motor in settings.motors if motor.enabled],
            runtime_directions,
        )


class TestSharedPWMDriverOwnership(unittest.TestCase):
    def setUp(self):
        self.adapter = PicarxAdapter.__new__(PicarxAdapter)
        self.adapter.smbus_manager = MagicMock()
        self.adapter._pwm_drivers = {}
        self.adapter._pwm_driver_configs = {}
        self.config = PWMDriverConfig(
            name="PCA9685",
            bus=1,
            address="0x40",
            frame_width=20000,
            freq=50,
        )

    @patch("app.adapters.picarx_adapter.PWMFactory.create_pwm_driver")
    def test_reuses_one_driver_per_physical_device(
        self, create_driver: MagicMock
    ) -> None:
        driver = MagicMock()
        create_driver.return_value = driver
        first = self.adapter._get_pwm_driver(self.config)
        second = self.adapter._get_pwm_driver(self.config.model_copy(deep=True))

        self.assertIs(first, second)
        create_driver.assert_called_once()
        driver.set_pwm_freq.assert_called_once_with(50)

    @patch("app.adapters.picarx_adapter.PWMFactory.create_pwm_driver")
    def test_reuses_driver_for_equivalent_address_notation(
        self, create_driver: MagicMock
    ) -> None:
        driver = MagicMock()
        create_driver.return_value = driver

        first = self.adapter._get_pwm_driver(self.config)
        second = self.adapter._get_pwm_driver(
            PWMDriverConfig(
                name="PCA9685",
                bus=1,
                address=0x40,
                frame_width=20000,
                freq=50,
            )
        )

        self.assertIs(first, second)
        create_driver.assert_called_once()

    @patch("app.adapters.picarx_adapter.PWMFactory.create_pwm_driver")
    def test_rejects_conflicting_config_for_same_device(
        self, _create_driver: MagicMock
    ) -> None:
        self.adapter._get_pwm_driver(self.config)

        with self.assertRaisesRegex(ValueError, "Conflicting PWM"):
            self.adapter._get_pwm_driver(self.config.model_copy(update={"freq": 60}))

    @patch("app.adapters.picarx_adapter.PWMFactory.create_pwm_driver")
    def test_failed_configuration_closes_uncached_driver(
        self, create_driver: MagicMock
    ) -> None:
        driver = MagicMock()
        driver.set_pwm_freq.side_effect = OSError("frequency")
        create_driver.return_value = driver

        with self.assertRaisesRegex(OSError, "frequency"):
            self.adapter._get_pwm_driver(self.config)

        driver.close.assert_called_once()
        self.assertEqual(self.adapter._pwm_drivers, {})

    def test_cleanup_closes_shared_driver_once_after_consumers(self) -> None:
        driver = MagicMock()
        self.adapter._pwm_drivers[(1, 0x40)] = driver
        self.adapter._pwm_driver_configs[(1, 0x40)] = self.config
        self.adapter.motor_controller = None
        self.adapter.motors = []
        self.adapter._motor_addresses = []
        self.adapter.steering_servo = None
        self.adapter.cam_tilt_servo = None
        self.adapter.cam_pan_servo = None

        self.adapter.cleanup()

        driver.close.assert_called_once()
        self.assertEqual(self.adapter._pwm_drivers, {})


if __name__ == "__main__":
    unittest.main()
