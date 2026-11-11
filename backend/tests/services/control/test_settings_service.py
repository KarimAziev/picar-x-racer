import json
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, call

from app.exceptions.settings import InvalidSettings
from app.schemas.robot.config import HardwareConfig, PartialHardwareConfig
from app.services.control.settings_service import SettingsService
from app.services.control.calibration_progress import calibration_snapshot


class TestSettingsServiceSharedPWMDrivers(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config_path = Path(__file__).resolve().parents[4] / "config.json"
        with config_path.open() as config_file:
            cls.config_data = json.load(config_file)

    def setUp(self) -> None:
        self.config_manager = MagicMock()
        self.config_manager.load_data.return_value = deepcopy(self.config_data)
        self.config_manager.update.side_effect = lambda data, **kwargs: data
        self.picarx = MagicMock()
        self.picarx.config = HardwareConfig.model_validate(self.config_data)
        self.service = SettingsService(
            cast(Any, self.picarx), cast(Any, self.config_manager)
        )

    def test_calibration_update_rejects_changed_settings_before_persistence(self):
        expected = self.service.saved_settings.model_copy(deep=True)
        self.service.saved_settings.ackermann_odometry.gear_ratio = 2
        with self.assertRaisesRegex(InvalidSettings, "settings changed"):
            self.service.merge_if_current(
                PartialHardwareConfig.model_validate(
                    {"pose_estimation": {"imu_yaw_bias_radps": 0.01}}
                ),
                expected,
            )
        self.config_manager.update.assert_not_called()

    def test_mounting_patch_preserves_driver_settings_and_saves_completion_atomically(
        self,
    ):
        for driver in ("sh3001", "lsm9ds1", "lsm6ds33", "mock"):
            with self.subTest(driver=driver):
                data = deepcopy(self.config_data)
                data["localization_sensors"]["imu"] = {
                    "driver": driver,
                    "enabled": False,
                    "frame_id": "mounted_imu",
                    "sample_frequency_hz": 80,
                }
                self.service.saved_settings = HardwareConfig.model_validate(data)
                update = PartialHardwareConfig.model_validate(
                    {
                        "localization_sensors": {
                            "imu": {
                                "driver": driver,
                                "transform": {
                                    "x_m": 0.16588,
                                    "y_m": -0.04,
                                    "z_m": 0.0438,
                                    "yaw_rad": -1.5707963267948966,
                                },
                            }
                        },
                    }
                )
                result = self.service.merge_settings(
                    update, calibration_step="imu_mount"
                )
                persisted = HardwareConfig.model_validate(
                    self.config_manager.update.call_args.args[0]
                )
                imu = persisted.localization_sensors.imu
                self.assertEqual(imu.driver, driver)
                self.assertFalse(imu.enabled)
                self.assertEqual(imu.frame_id, "mounted_imu")
                self.assertEqual(imu.sample_frequency_hz, 80)
                self.assertEqual(imu.transform.z_m, 0.0438)
                self.assertEqual(
                    persisted.calibration_progress["imu_mount"],
                    calibration_snapshot(persisted, "imu_mount"),
                )
                self.assertEqual(
                    result.calibration_progress, persisted.calibration_progress
                )
                self.assertNotIn(
                    "imu_mount", self.service.saved_settings.calibration_progress
                )

    def test_failed_measurement_save_does_not_mark_completion(self):
        self.config_manager.update.side_effect = OSError("disk full")
        with self.assertRaisesRegex(OSError, "disk full"):
            self.service.merge_settings(
                PartialHardwareConfig.model_validate(
                    {"pose_estimation": {"imu_yaw_bias_radps": 0}}
                ),
                calibration_step="imu_bias",
            )
        self.assertEqual(self.service.saved_settings.calibration_progress, {})

    def test_completion_snapshot_round_trips_and_detects_changed_dependencies(self):
        config = self.service.saved_settings.model_copy(deep=True)
        for step in (
            "body",
            "lidar_mount",
            "imu_mount",
            "wheel_distance",
            "speed",
            "imu_bias",
            "steering_center",
            "steering_range",
            "stopping",
        ):
            config.calibration_progress[step] = calibration_snapshot(config, step)
        restored = HardwareConfig.model_validate_json(config.model_dump_json())
        self.assertEqual(restored.calibration_progress, config.calibration_progress)
        restored.localization_sensors.imu.transform.yaw_rad = 1
        self.assertNotEqual(
            restored.calibration_progress["imu_bias"],
            calibration_snapshot(restored, "imu_bias"),
        )
        self.assertNotEqual(
            restored.calibration_progress["imu_mount"],
            calibration_snapshot(restored, "imu_mount"),
        )
        self.assertEqual(
            restored.calibration_progress["body"],
            calibration_snapshot(restored, "body"),
        )

    def test_odometry_setup_error_points_to_motion_control_without_debug_dump(
        self,
    ) -> None:
        update = PartialHardwareConfig.model_validate(
            {
                "ackermann_odometry": {
                    "enabled": True,
                    "wheelbase_m": 0.26,
                    "wheel_radius_m": 0.03,
                    "encoder_ticks_per_revolution": 4096,
                },
                "localization_sensors": {
                    "encoder": {
                        "enabled": True,
                        "sensors": [{"driver": "mock", "role": "rear_axle_average"}],
                    },
                },
            }
        )
        with self.assertRaises(InvalidSettings) as caught:
            self.service.merge_settings(update)
        message = str(caught.exception)
        self.assertIn("Robot > Motion control", message)
        self.assertIn("measured forward and reverse speeds", message)
        self.assertNotIn("input_value", message)
        self.assertNotIn("pydantic.dev", message)
        self.picarx.init_hardware.assert_not_called()
        self.config_manager.update.assert_not_called()

    def make_steering_update(self, **driver_updates: Any) -> PartialHardwareConfig:
        steering = deepcopy(self.config_data["steering_servo"])
        steering["driver"].update(driver_updates)
        return PartialHardwareConfig.model_validate({"steering_servo": steering})

    def test_rejects_conflicting_shared_driver_before_writing_or_cleanup(self) -> None:
        update = self.make_steering_update(name="PCA9685")

        with self.assertRaisesRegex(
            InvalidSettings,
            r"cam_pan_servo uses Sunfounder.*steering_servo uses PCA9685",
        ):
            self.service.merge_settings(update)

        self.config_manager.update.assert_not_called()
        self.picarx.cleanup.assert_not_called()
        self.picarx.init_hardware.assert_not_called()

    def test_rejects_invalid_partial_autonomy_relationship_before_activation(
        self,
    ) -> None:
        update = PartialHardwareConfig.model_validate(
            {
                "lidar_safety": {
                    "enabled": True,
                    "stop_distance_m": 0.3,
                    "slow_distance_m": 1.0,
                }
            }
        )

        with self.assertRaisesRegex(
            InvalidSettings,
            "Robot > Motion control",
        ):
            self.service.merge_settings(update)

        self.config_manager.update.assert_not_called()
        self.picarx.cleanup.assert_not_called()
        self.picarx.init_hardware.assert_not_called()

    def test_persists_autonomy_update_without_reinitializing_picarx(self) -> None:
        self.service.saved_settings.motion_control.max_forward_speed_mps = 1.2
        self.service.saved_settings.motion_control.max_reverse_speed_mps = 0.6
        update = PartialHardwareConfig.model_validate(
            {"motion_control": {"control_frequency_hz": 25}}
        )

        saved = self.service.merge_settings(update)

        self.assertEqual(saved.motion_control.control_frequency_hz, 25)
        self.config_manager.update.assert_called_once()
        persisted = self.config_manager.update.call_args.args[0]
        self.assertEqual(persisted["motion_control"]["control_frequency_hz"], 25)
        self.assertEqual(persisted["motion_control"]["max_forward_speed_mps"], 1.2)
        self.assertEqual(persisted["motion_control"]["max_reverse_speed_mps"], 0.6)
        self.picarx.cleanup.assert_not_called()
        self.picarx.init_hardware.assert_not_called()

    def test_accepts_equivalent_hex_and_integer_addresses(self) -> None:
        candidate_data = deepcopy(self.config_data)
        candidate_data["steering_servo"]["driver"]["address"] = 0x14
        candidate = HardwareConfig.model_validate(candidate_data)

        self.service._validate_shared_pwm_drivers(candidate)

    def test_rejects_led_motor_enable_collision_before_activation(self) -> None:
        candidate_data = deepcopy(self.config_data)
        candidate_data["motors"] = [
            {
                "name": "Drive",
                "forward_pin": "GPIO20",
                "backward_pin": "GPIO21",
                "enable_pin": "GPIO26",
            }
        ]
        candidate_data["led"] = {"name": "LED", "pin": 26, "interval": 0.1}
        candidate = HardwareConfig.model_validate(candidate_data)

        with self.assertRaisesRegex(InvalidSettings, "LED GPIO26 is reserved"):
            self.service.save_settings(candidate)

        self.picarx.cleanup.assert_not_called()
        self.config_manager.update.assert_not_called()

    def _gpio_motor_candidate(self, enable_pin: str) -> HardwareConfig:
        candidate_data = deepcopy(self.config_data)
        candidate_data["motors"] = [
            {
                "name": "Drive",
                "forward_pin": "GPIO20",
                "backward_pin": "GPIO21",
                "enable_pin": enable_pin,
            }
        ]
        candidate_data["led"] = None
        candidate_data["ultrasonic"] = None
        return HardwareConfig.model_validate(candidate_data)

    def test_cannot_assign_motor_to_led_pin_in_same_update_that_disables_led(
        self,
    ) -> None:
        candidate = self._gpio_motor_candidate("GPIO26")

        with self.assertRaisesRegex(InvalidSettings, "GPIO26 is still reserved by LED"):
            self.service.save_settings(candidate)

        self.picarx.cleanup.assert_not_called()
        self.config_manager.update.assert_not_called()

    def test_runtime_led_pin_is_reserved_during_actuator_initialization(self) -> None:
        self.service._led_service = MagicMock()
        self.service._led_service.led_config.pin = "GPIO25"
        candidate = self._gpio_motor_candidate("GPIO25")

        with self.assertRaisesRegex(InvalidSettings, "GPIO25 is still reserved by LED"):
            self.service.save_settings(candidate)

        self.picarx.cleanup.assert_not_called()

    def test_cannot_assign_motor_to_running_ultrasonic_gpio(self) -> None:
        self.service._distance_service = MagicMock()
        self.service._distance_service.robot_config = (
            self.service.saved_settings.model_copy(deep=True)
        )
        self.service.saved_settings.ultrasonic = None
        candidate = self._gpio_motor_candidate("GPIO27")

        with self.assertRaisesRegex(
            InvalidSettings, "GPIO27 is still reserved by ultrasonic trigger"
        ):
            self.service.save_settings(candidate)

        self.picarx.cleanup.assert_not_called()

    def test_can_claim_led_gpio_after_led_disable_has_been_applied(self) -> None:
        self.service.saved_settings.led = None
        self.service._led_service = MagicMock(led_config=None)
        candidate = self._gpio_motor_candidate("GPIO26")

        self.service.save_settings(candidate)

        self.picarx.init_hardware.assert_called_once()
        self.config_manager.update.assert_called_once()

    def test_failed_strict_initialization_restores_previous_hardware(self) -> None:
        update = self.make_steering_update()
        update.steering_servo.min_angle = -35
        self.picarx.init_hardware.side_effect = [OSError("device offline"), None]

        with self.assertRaisesRegex(
            InvalidSettings, "Unable to apply hardware settings: device offline"
        ):
            self.service.merge_settings(update)

        self.config_manager.update.assert_not_called()
        self.assertEqual(self.picarx.cleanup.call_count, 2)
        first_config = self.picarx.init_hardware.call_args_list[0].kwargs["config"]
        self.assertEqual(first_config.steering_servo.min_angle, -35)
        self.assertEqual(
            self.picarx.init_hardware.call_args_list,
            [
                call(config=first_config, strict=True),
                call(config=self.picarx.config.model_copy(deep=True)),
            ],
        )

    def test_persists_only_after_strict_initialization_succeeds(self) -> None:
        update = self.make_steering_update()
        update.steering_servo.min_angle = -35

        saved = self.service.merge_settings(update)

        self.picarx.init_hardware.assert_called_once()
        init_config = self.picarx.init_hardware.call_args.kwargs["config"]
        self.assertEqual(init_config.steering_servo.min_angle, -35)
        self.assertTrue(self.picarx.init_hardware.call_args.kwargs["strict"])
        self.config_manager.update.assert_called_once()
        self.assertEqual(saved.steering_servo.min_angle, -35)


if __name__ == "__main__":
    unittest.main()
