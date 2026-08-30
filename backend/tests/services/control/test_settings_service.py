import json
import unittest
from copy import deepcopy
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, call

from app.exceptions.settings import InvalidSettings
from app.schemas.robot.config import HardwareConfig, PartialHardwareConfig
from app.services.control.settings_service import SettingsService


class TestSettingsServiceSharedPWMDrivers(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        config_path = Path(__file__).resolve().parents[4] / "config.json"
        with config_path.open() as config_file:
            cls.config_data = json.load(config_file)

    def setUp(self) -> None:
        self.config_manager = MagicMock()
        self.config_manager.load_data.return_value = deepcopy(self.config_data)
        self.config_manager.update.side_effect = lambda data: data
        self.picarx = MagicMock()
        self.picarx.config = HardwareConfig.model_validate(self.config_data)
        self.service = SettingsService(
            cast(Any, self.picarx), cast(Any, self.config_manager)
        )

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

    def test_accepts_equivalent_hex_and_integer_addresses(self) -> None:
        candidate_data = deepcopy(self.config_data)
        candidate_data["steering_servo"]["driver"]["address"] = 0x14
        candidate = HardwareConfig.model_validate(candidate_data)

        self.service._validate_shared_pwm_drivers(candidate)

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
