import asyncio
import unittest
from pathlib import Path
from threading import Event, RLock
from unittest.mock import Mock, patch

from app.adapters.picarx_adapter import PicarxAdapter
from app.schemas.robot.config import HardwareConfig
from app.services.control.car_service import CarService
from app.schemas.robot.servos import AngularServoConfig, GPIOAngularServoConfig
from pydantic import ValidationError
from robot_hat import ServoCalibrationMode


class TestServoAngleCalibration(unittest.TestCase):
    def setUp(self) -> None:
        self.adapter = PicarxAdapter.__new__(PicarxAdapter)
        self.driver = Mock()

    def test_servo_reverse_is_applied_to_requested_angles(self):
        config = AngularServoConfig(
            name="Steering",
            channel="P11",
            min_angle=-30,
            max_angle=30,
            min_pulse=1000,
            max_pulse=2000,
            real_min_angle=-45,
            real_max_angle=45,
            calibration_mode=ServoCalibrationMode.SUM,
            reverse=True,
        )
        with patch.object(self.adapter, "_get_pwm_driver", return_value=self.driver):
            service = self.adapter._make_servo(config)
            service.set_angle(9)
            self.driver.set_servo_pulse.assert_called_with(11, 1400)
            service.close()

    def test_reversed_servo_state_and_opposite_commands_use_logical_angles(
        self,
    ) -> None:
        for reverse in (False, True):
            for mode in (ServoCalibrationMode.SUM, ServoCalibrationMode.NEGATIVE):
                with self.subTest(reverse=reverse, mode=mode):
                    config = AngularServoConfig(
                        name="Steering",
                        channel="P11",
                        min_angle=-10,
                        max_angle=30,
                        min_pulse=1000,
                        max_pulse=2000,
                        real_min_angle=-45,
                        real_max_angle=45,
                        calibration_mode=mode,
                        reverse=reverse,
                    )
                    self.adapter.config = HardwareConfig.model_validate_json(
                        (
                            Path(__file__).resolve().parents[4] / "config.json"
                        ).read_text()
                    )
                    self.adapter.config.steering_servo = config
                    self.adapter.config.cam_pan_servo = config
                    self.adapter.config.cam_tilt_servo = config
                    self.adapter._hardware_lock = RLock()
                    self.adapter._shutdown_requested = Event()
                    self.adapter.motor_controller = None
                    with patch.object(
                        self.adapter, "_get_pwm_driver", return_value=self.driver
                    ):
                        servo = self.adapter._make_servo(config)
                    self.addCleanup(servo.close)
                    self.adapter.steering_servo = servo
                    self.adapter.cam_pan_servo = servo
                    self.adapter.cam_tilt_servo = servo
                    car = CarService.__new__(CarService)
                    car.px = self.adapter
                    car.motion_control_service = None
                    for handler in (
                        car.handle_set_servo_dir_angle,
                        car.handle_set_cam_pan_angle,
                        car.handle_set_cam_tilt_angle,
                    ):
                        for angle in (-9, 9, -9):
                            asyncio.run(handler(angle))
                            for key in (
                                "steering_servo_angle",
                                "cam_pan_angle",
                                "cam_tilt_angle",
                            ):
                                self.assertEqual(self.adapter.state[key], angle)
                            physical = (
                                angle
                                * (-1 if reverse else 1)
                                * (-1 if mode == ServoCalibrationMode.NEGATIVE else 1)
                            )
                            expected_pulse = 1500 + physical / 90 * 1000
                            self.driver.set_servo_pulse.assert_called_with(
                                11, round(expected_pulse)
                            )
                    asyncio.run(car.handle_set_servo_dir_angle(100))
                    self.assertEqual(
                        self.adapter.state["steering_servo_angle"],
                        10 if reverse else 30,
                    )

    def test_i2c_travel_limits_preserve_pulse_scale(self) -> None:
        for limit, low, high in ((30, 1267, 1733), (10, 1422, 1578)):
            config = AngularServoConfig(
                name="Steering",
                channel="P11",
                min_angle=-limit,
                max_angle=limit,
                min_pulse=800,
                max_pulse=2200,
                calibration_mode=ServoCalibrationMode.SUM,
            )
            with self.subTest(limit=limit), patch.object(
                self.adapter, "_get_pwm_driver", return_value=self.driver
            ):
                service = self.adapter._make_servo(config)
                self.driver.set_servo_pulse.assert_called_with(11, 1500)
                service.set_angle(-100)
                self.driver.set_servo_pulse.assert_called_with(11, low)
                service.set_angle(100)
                self.driver.set_servo_pulse.assert_called_with(11, high)
                service.set_angle(5)
                self.driver.set_servo_pulse.assert_called_with(11, 1539)
                service.close()

    def test_center_offset_is_applied_after_travel_limit(self) -> None:
        for mode, expected in (
            (ServoCalibrationMode.SUM, 1667),
            (ServoCalibrationMode.NEGATIVE, 1444),
        ):
            config = AngularServoConfig(
                name="Steering",
                channel="P11",
                min_angle=-10,
                max_angle=10,
                min_pulse=1000,
                max_pulse=2000,
                real_min_angle=-45,
                real_max_angle=45,
                calibration_offset=5,
                calibration_mode=mode,
            )
            with self.subTest(mode=mode), patch.object(
                self.adapter, "_get_pwm_driver", return_value=self.driver
            ):
                service = self.adapter._make_servo(config)
                service.set_angle(100)
                self.assertEqual(service.current_angle, 10)
                self.driver.set_servo_pulse.assert_called_with(11, expected)
                service.close()

    def test_gpio_uses_calibration_endpoints_and_service_limits(self) -> None:
        config = GPIOAngularServoConfig(
            name="Steering",
            pin=17,
            min_angle=-10,
            max_angle=10,
            real_min_angle=-45,
            real_max_angle=45,
            min_pulse=1000,
            max_pulse=2000,
            calibration_offset=5,
            calibration_mode=ServoCalibrationMode.SUM,
        )
        with patch("gpiozero.AngularServo") as gpio:
            service = self.adapter._make_servo(config)
            gpio.assert_called_once_with(
                17,
                initial_angle=None,
                min_angle=-45,
                max_angle=45,
                min_pulse_width=0.001,
                max_pulse_width=0.002,
            )
            self.assertEqual(gpio.return_value.angle, 5)
            service.set_angle(100)
            self.assertEqual(gpio.return_value.angle, 15)
            service.set_angle(-100)
            self.assertEqual(gpio.return_value.angle, -5)
            service.close()

    def test_calibration_defaults_accept_existing_config(self) -> None:
        config = AngularServoConfig.model_validate(
            {"name": "Steering", "channel": "P11", "min_angle": -10, "max_angle": 10}
        )
        self.assertEqual(config.real_min_angle, -90)
        self.assertEqual(config.real_max_angle, 90)

    def test_invalid_calibration_endpoints_are_rejected(self) -> None:
        for lower, upper in (
            (10, 10),
            (20, 10),
            (float("nan"), 90),
            (-90, float("inf")),
        ):
            with self.subTest(lower=lower, upper=upper), self.assertRaises(
                ValidationError
            ):
                AngularServoConfig(
                    name="Steering",
                    channel="P11",
                    real_min_angle=lower,
                    real_max_angle=upper,
                )


if __name__ == "__main__":
    unittest.main()
