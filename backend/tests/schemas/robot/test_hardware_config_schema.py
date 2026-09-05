import unittest
from typing import Any, Dict

from app.schemas.robot.config import HardwareConfig


class TestHardwareConfigSchemaMetadata(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = HardwareConfig.model_json_schema()

    def object_schemas(self) -> Dict[str, Dict[str, Any]]:
        definitions = self.schema.get("$defs", {})
        return {
            "HardwareConfig": self.schema,
            **{
                name: definition
                for name, definition in definitions.items()
                if definition.get("properties")
            },
        }

    def test_every_hardware_config_field_has_ui_metadata(self) -> None:
        missing = []
        for model_name, model_schema in self.object_schemas().items():
            for field_name, field_schema in model_schema["properties"].items():
                for keyword in ("title", "description"):
                    if not field_schema.get(keyword):
                        missing.append(f"{model_name}.{field_name}.{keyword}")

        self.assertEqual(
            missing,
            [],
            "HardwareConfig fields missing human-facing JSON Schema metadata",
        )

    def test_every_hardware_config_object_has_panel_metadata(self) -> None:
        missing = []
        for model_name, model_schema in self.object_schemas().items():
            for keyword in ("title", "description"):
                if not model_schema.get(keyword):
                    missing.append(f"{model_name}.{keyword}")

        self.assertEqual(
            missing,
            [],
            "HardwareConfig objects missing human-facing panel metadata",
        )

    def test_frontend_visible_objects_have_readable_titles(self) -> None:
        definitions = self.schema["$defs"]
        expected_titles = {
            "RPLidarC1SensorConfig": "RPLIDAR C1",
            "MockLidarSensorConfig": "Mock LiDAR",
            "SH3001SensorConfig": "SH3001 IMU",
            "LSM9DS1SensorConfig": "LSM9DS1 IMU",
            "MockIMUSensorConfig": "Mock IMU",
            "AS5048AEncoderConfig": "AS5048A drive encoder",
            "AS5600LEncoderConfig": "AS5600L drive encoder",
            "GPIOQuadratureEncoderConfig": "GPIO quadrature drive encoder",
            "MockEncoderConfig": "Mock drive encoder",
            "AS5048ASteeringPositionConfig": "AS5048A steering position",
            "AS5600LSteeringPositionConfig": "AS5600L steering position",
            "MockSteeringPositionConfig": "Mock steering position",
            "SteeringCalibrationPointConfig": "Steering calibration point",
            "I2CDCMotorConfig": "I2C PWM DC motor",
            "GPIODCMotorConfig": "GPIO dual-input DC motor",
            "PhaseMotorConfig": "GPIO phase-and-enable DC motor",
            "AngularServoConfig": "I2C PWM servo",
            "GPIOAngularServoConfig": "GPIO PWM servo",
            "SunfounderBatteryConfig": "SunFounder Robot HAT battery monitor",
            "INA219BatteryDriverConfig": "INA219 battery monitor",
            "INA226BatteryDriverConfig": "INA226 battery monitor",
            "INA260BatteryDriverConfig": "INA260 battery monitor",
            "BatteryConfig": "Battery monitor",
            "UltrasonicConfig": "Ultrasonic distance sensor",
            "LedConfig": "LED",
        }

        for definition_name, expected_title in expected_titles.items():
            with self.subTest(definition=definition_name):
                self.assertEqual(definitions[definition_name]["title"], expected_title)

    def test_localization_shared_and_widget_metadata_is_preserved(self) -> None:
        definitions = self.schema["$defs"]
        lidar = definitions["RPLidarC1SensorConfig"]["properties"]
        encoder = definitions["AS5048AEncoderConfig"]["properties"]
        gpio_encoder = definitions["GPIOQuadratureEncoderConfig"]["properties"]
        imu = definitions["SH3001SensorConfig"]["properties"]

        for field_name in (
            "enabled",
            "frame_id",
            "transform",
            "range_min_m",
            "range_max_m",
            "angular_resolution_deg",
            "min_measurements_per_scan",
        ):
            with self.subTest(field_name=field_name):
                self.assertTrue(lidar[field_name]["shared"])

        for field_name in ("side", "invert_direction", "bus", "device"):
            with self.subTest(field_name=field_name):
                self.assertTrue(encoder[field_name]["shared"])

        self.assertEqual(gpio_encoder["a_pin"]["x-ui-type"], "pin")
        self.assertEqual(gpio_encoder["b_pin"]["x-ui-type"], "pin")
        self.assertTrue(imu["bus"]["shared"])

        encoder_list = definitions["EncoderSensorConfig"]["properties"]["sensors"]
        self.assertEqual(encoder_list["props"]["typeLabel"], "Encoder type")
        self.assertEqual(
            self.schema["properties"]["motors"]["props"]["typeLabel"],
            "Motor type",
        )


if __name__ == "__main__":
    unittest.main()
