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

        self.assertEqual(result.applied_versions, (1,))
        self.assertEqual(result.data["schema_version"], 1)
        self.assertNotIn("left_motor", result.data)
        self.assertNotIn("right_motor", result.data)
        self.assertEqual(
            [motor["channel"] for motor in result.data["motors"]],
            ["P12", "P13"],
        )
        self.assertNotIn("pwm_pin", result.data["motors"][0])
        self.assertNotIn("period", result.data["motors"][0])
        HardwareConfig.model_validate(result.data)

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
            self.assertEqual(persisted["schema_version"], 1)
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

            self.assertEqual(manager.load_data()["schema_version"], 1)
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
