import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from app.managers.file_management.json_data_manager import JsonDataManager
from app.migrations.json_data import JsonDataMigrationError, JsonObject
from app.migrations.robot_config import create_robot_config_migrator
from app.migrations.robot_config.v8_servo_pulse_calibration import migrate_to_v8
from app.schemas.robot.config import HardwareConfig
from pydantic import ValidationError


class TestServoPulseCalibrationMigration(unittest.TestCase):
    def setUp(self) -> None:
        template = Path(__file__).resolve().parents[3] / "config.json"
        self.data: JsonObject = json.loads(template.read_text())
        self.data["schema_version"] = 7
        for name in ("steering_servo", "cam_pan_servo", "cam_tilt_servo"):
            self.data[name].pop("real_min_angle")
            self.data[name].pop("real_max_angle")
        self.data["steering_servo"].update(
            enabled=False,
            min_angle=-10,
            max_angle=15,
            calibration_offset=2,
            min_pulse=1000,
            max_pulse=2000,
        )

    def test_direct_transform_preserves_limits_pulses_and_other_fields(self) -> None:
        result = migrate_to_v8(deepcopy(self.data))
        for name in ("steering_servo", "cam_pan_servo", "cam_tilt_servo"):
            self.assertEqual(result[name].pop("real_min_angle"), -90)
            self.assertEqual(result[name].pop("real_max_angle"), 90)
        self.assertEqual(result, self.data)

    def test_preserves_explicit_calibration_for_i2c_and_gpio_servos(self) -> None:
        servo = self.data["cam_pan_servo"]
        servo.pop("channel")
        servo.pop("driver")
        servo.update(pin=17, real_min_angle=-45, real_max_angle=45)
        expected = deepcopy(servo)
        result = create_robot_config_migrator().migrate(self.data)
        self.assertEqual(result.data["cam_pan_servo"], expected)
        self.assertEqual(result.applied_versions, (8,))
        self.assertEqual(HardwareConfig.model_validate(result.data).schema_version, 8)
        self.assertNotIn("real_min_angle", self.data["steering_servo"])

    def test_v6_runs_encoder_and_servo_migrations_in_order(self) -> None:
        self.data["schema_version"] = 6
        self.data["localization_sensors"]["encoder"]["sensors"] = [
            {"side": "left", "driver": "mock"}
        ]
        result = create_robot_config_migrator().migrate(self.data)
        self.assertEqual(result.applied_versions, (7, 8))
        self.assertEqual(result.data["steering_servo"]["real_min_angle"], -90)
        self.assertEqual(
            result.data["localization_sensors"]["encoder"]["sensors"][0]["role"],
            "left_wheel",
        )
        self.assertFalse(create_robot_config_migrator().migrate(result.data).changed)

    def test_rejects_incomplete_calibration_pair(self) -> None:
        for field in ("real_min_angle", "real_max_angle"):
            data = deepcopy(self.data)
            data["steering_servo"][field] = 10
            with self.subTest(field=field), self.assertRaisesRegex(
                JsonDataMigrationError, "must specify both"
            ):
                create_robot_config_migrator().migrate(data)

    def test_rejects_invalid_servo_shape(self) -> None:
        for value in (None, [], "disabled"):
            self.data["steering_servo"] = value
            with self.assertRaisesRegex(JsonDataMigrationError, "must be an object"):
                create_robot_config_migrator().migrate(self.data)

    def test_manager_atomically_persists_upgrade_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config.json"
            target.write_text(json.dumps(self.data))
            replace = Path.replace
            replacements: list[tuple[Path, Path]] = []

            def record_replace(source: Path, destination: Path) -> Path:
                self.assertEqual(json.loads(target.read_text()), self.data)
                self.assertEqual(json.loads(source.read_text())["schema_version"], 8)
                replacements.append((source, destination))
                return replace(source, destination)

            with patch.object(Path, "replace", record_replace):
                manager = JsonDataManager(
                    str(target), str(target), migrator=create_robot_config_migrator()
                )
                manager.load_data()
            self.assertEqual(len(replacements), 1)
            self.assertEqual(manager.load_data(), json.loads(target.read_text()))
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_invalid_calibration_does_not_overwrite_target(self) -> None:
        self.data["steering_servo"].update(real_min_angle=45, real_max_angle=-45)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config.json"
            original = json.dumps(self.data)
            target.write_text(original)
            with self.assertRaises(ValidationError):
                JsonDataManager(
                    str(target), str(target), migrator=create_robot_config_migrator()
                )
            self.assertEqual(target.read_text(), original)

    def test_failed_atomic_replace_keeps_original_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config.json"
            original = json.dumps(self.data)
            target.write_text(original)
            with patch.object(Path, "replace", side_effect=OSError("disk failure")):
                with self.assertRaises(OSError):
                    JsonDataManager(
                        str(target),
                        str(target),
                        migrator=create_robot_config_migrator(),
                    )
            self.assertEqual(target.read_text(), original)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_template_upgrade_does_not_write_runtime_config_or_template(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "config.json"
            template = Path(directory) / "template.json"
            original = json.dumps(self.data)
            template.write_text(original)
            manager = JsonDataManager(
                str(target), str(template), migrator=create_robot_config_migrator()
            )
            self.assertEqual(manager.load_data()["schema_version"], 8)
            self.assertFalse(target.exists())
            self.assertEqual(template.read_text(), original)


if __name__ == "__main__":
    unittest.main()
