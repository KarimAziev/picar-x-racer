import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from app.managers.file_management.json_data_manager import JsonDataManager
from app.migrations.json_data import JsonDataMigrationError
from app.migrations.robot_config import create_robot_config_migrator
from app.schemas.robot.config import HardwareConfig
from pydantic import ValidationError


class TestRobotConfigMigration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config_path = Path(__file__).resolve().parents[3] / "config.json"
        with config_path.open() as config_file:
            cls.current_config = json.load(config_file)

    def make_legacy_config(self):
        data = deepcopy(self.current_config)
        data.pop("schema_version")
        data.pop("motion_control")
        data.pop("ackermann_odometry")
        data.pop("localization_sensors")
        battery = data.pop("batteries")[0]
        battery.pop("name")
        data["battery"] = battery
        motors = data.pop("motors")
        for motor in motors:
            motor["pwm_pin"] = motor.pop("channel")
            motor["calibration_speed_offset"] = 0.0
            motor["period"] = 4095
            motor["prescaler"] = 10
        data["left_motor"], data["right_motor"] = motors
        return data

    def test_migrates_legacy_motor_fields(self):
        result = create_robot_config_migrator().migrate(self.make_legacy_config())

        self.assertEqual(result.applied_versions, (1, 2, 3, 4, 5))
        self.assertEqual(result.data["schema_version"], 5)
        self.assertNotIn("left_motor", result.data)
        self.assertNotIn("right_motor", result.data)
        self.assertEqual(
            [motor["channel"] for motor in result.data["motors"]],
            ["P12", "P13"],
        )
        self.assertNotIn("pwm_pin", result.data["motors"][0])
        self.assertNotIn("period", result.data["motors"][0])
        self.assertNotIn("battery", result.data)
        self.assertEqual(result.data["batteries"][0]["name"], "Main battery")
        self.assertEqual(result.data["motion_control"], {"enabled": False})
        self.assertEqual(result.data["ackermann_odometry"], {"enabled": False})
        self.assertEqual(
            result.data["localization_sensors"],
            {
                "lidar": {"enabled": False},
                "imu": {"enabled": False},
                "encoder": {"enabled": False},
            },
        )
        HardwareConfig.model_validate(result.data)

    def test_migrates_v1_battery_to_named_collection(self):
        data = deepcopy(self.current_config)
        data["schema_version"] = 1
        battery = data.pop("batteries")[0]
        battery.pop("name")
        data["battery"] = battery

        result = create_robot_config_migrator().migrate(data)

        self.assertEqual(result.applied_versions, (2, 3, 4, 5))
        self.assertEqual(result.data["schema_version"], 5)
        self.assertEqual(result.data["batteries"][0]["name"], "Main battery")

    def test_migrates_v2_with_disabled_motion_control(self):
        data = deepcopy(self.current_config)
        data["schema_version"] = 2
        data.pop("motion_control")

        result = create_robot_config_migrator().migrate(data)

        self.assertEqual(result.applied_versions, (3, 4, 5))
        self.assertEqual(result.data["schema_version"], 5)
        self.assertEqual(result.data["motion_control"], {"enabled": False})
        HardwareConfig.model_validate(result.data)

    def test_v3_preserves_prerelease_motion_control_values(self):
        data = deepcopy(self.current_config)
        data["schema_version"] = 2
        data["motion_control"] = {
            "enabled": True,
            "control_frequency_hz": 25,
            "command_timeout_ms": 200,
            "max_forward_speed_mps": 0.8,
            "max_reverse_speed_mps": 0.4,
        }

        result = create_robot_config_migrator().migrate(data)

        self.assertEqual(result.data["motion_control"], data["motion_control"])

    def test_v3_rejects_invalid_motion_control_shape(self):
        data = deepcopy(self.current_config)
        data["schema_version"] = 2
        data["motion_control"] = "enabled"

        with self.assertRaisesRegex(JsonDataMigrationError, "must be an object"):
            create_robot_config_migrator().migrate(data)

    def test_migrates_v3_with_disabled_ackermann_odometry(self):
        data = deepcopy(self.current_config)
        data["schema_version"] = 3
        data.pop("ackermann_odometry")

        result = create_robot_config_migrator().migrate(data)

        self.assertEqual(result.applied_versions, (4, 5))
        self.assertEqual(result.data["schema_version"], 5)
        self.assertEqual(result.data["ackermann_odometry"], {"enabled": False})
        HardwareConfig.model_validate(result.data)

    def test_v4_preserves_prerelease_odometry_values(self):
        data = deepcopy(self.current_config)
        data["schema_version"] = 3
        data["ackermann_odometry"] = {
            "enabled": True,
            "wheelbase_m": 0.15,
            "wheel_radius_m": 0.03,
            "encoder_ticks_per_revolution": 20,
            "gear_ratio": 2.0,
            "max_steering_age_ms": 200,
        }

        result = create_robot_config_migrator().migrate(data)

        self.assertEqual(
            result.data["ackermann_odometry"],
            data["ackermann_odometry"],
        )

    def test_v4_rejects_invalid_ackermann_odometry_shape(self):
        data = deepcopy(self.current_config)
        data["schema_version"] = 3
        data["ackermann_odometry"] = "enabled"

        with self.assertRaisesRegex(JsonDataMigrationError, "must be an object"):
            create_robot_config_migrator().migrate(data)

    def test_migrates_v4_with_disabled_localization_sensors(self):
        data = deepcopy(self.current_config)
        data["schema_version"] = 4
        data.pop("localization_sensors")

        result = create_robot_config_migrator().migrate(data)

        self.assertEqual(result.applied_versions, (5,))
        self.assertEqual(result.data["schema_version"], 5)
        self.assertEqual(
            result.data["localization_sensors"],
            {
                "lidar": {"enabled": False},
                "imu": {"enabled": False},
                "encoder": {"enabled": False},
            },
        )
        HardwareConfig.model_validate(result.data)

    def test_v5_preserves_prerelease_localization_sensor_values(self):
        data = deepcopy(self.current_config)
        data["schema_version"] = 4
        data["localization_sensors"] = {
            "lidar": {
                "enabled": True,
                "range_min_m": 0.05,
                "range_max_m": 12.0,
            },
            "imu": {"enabled": True, "sample_frequency_hz": 50},
            "encoder": {"enabled": False},
        }

        result = create_robot_config_migrator().migrate(data)

        self.assertEqual(
            result.data["localization_sensors"],
            data["localization_sensors"],
        )

    def test_v5_rejects_invalid_localization_sensor_shape(self):
        data = deepcopy(self.current_config)
        data["schema_version"] = 4
        data["localization_sensors"] = "enabled"

        with self.assertRaisesRegex(JsonDataMigrationError, "must be an object"):
            create_robot_config_migrator().migrate(data)

    def test_rejects_ambiguous_battery_shapes(self):
        data = deepcopy(self.current_config)
        data["schema_version"] = 1
        data["battery"] = deepcopy(data["batteries"][0])

        with self.assertRaisesRegex(JsonDataMigrationError, "both legacy"):
            create_robot_config_migrator().migrate(data)

    def test_rejects_invalid_legacy_battery(self):
        data = deepcopy(self.current_config)
        data["schema_version"] = 1
        data.pop("batteries")
        data["battery"] = "invalid"

        with self.assertRaisesRegex(JsonDataMigrationError, "must be an object"):
            create_robot_config_migrator().migrate(data)

    def test_rejects_duplicate_battery_names(self):
        data = deepcopy(self.current_config)
        duplicate = deepcopy(data["batteries"][0])
        duplicate["name"] = " main BATTERY "
        data["batteries"].append(duplicate)

        with self.assertRaisesRegex(ValidationError, "names must be unique"):
            HardwareConfig.model_validate(data)

    def test_rejects_ambiguous_motor_shapes(self):
        data = self.make_legacy_config()
        data["motors"] = deepcopy(self.current_config["motors"])

        with self.assertRaisesRegex(JsonDataMigrationError, "both legacy"):
            create_robot_config_migrator().migrate(data)

    def test_manager_persists_migrated_target(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "config.json"
            template = Path(temp_dir) / "default.json"
            target.write_text(json.dumps(self.make_legacy_config()))
            template.write_text(json.dumps(self.current_config))

            manager = JsonDataManager(
                str(target),
                str(template),
                migrator=create_robot_config_migrator(),
            )

            persisted = json.loads(target.read_text())
            self.assertEqual(manager.load_data(), persisted)
            self.assertEqual(persisted["schema_version"], 5)
            self.assertIn("motors", persisted)
            self.assertNotIn("left_motor", persisted)

    def test_manager_does_not_materialize_migrated_template(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "config.json"
            template = Path(temp_dir) / "default.json"
            template.write_text(json.dumps(self.make_legacy_config()))

            manager = JsonDataManager(
                str(target),
                str(template),
                migrator=create_robot_config_migrator(),
            )

            self.assertEqual(manager.load_data()["schema_version"], 5)
            self.assertFalse(target.exists())

    def test_manager_does_not_overwrite_invalid_migration(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "config.json"
            template = Path(temp_dir) / "default.json"
            invalid_data = self.make_legacy_config()
            invalid_data["left_motor"] = None
            invalid_data["right_motor"] = None
            original = json.dumps(invalid_data)
            target.write_text(original)
            template.write_text(json.dumps(self.current_config))

            with self.assertRaises(ValidationError):
                JsonDataManager(
                    str(target),
                    str(template),
                    migrator=create_robot_config_migrator(),
                )

            self.assertEqual(target.read_text(), original)


if __name__ == "__main__":
    unittest.main()
