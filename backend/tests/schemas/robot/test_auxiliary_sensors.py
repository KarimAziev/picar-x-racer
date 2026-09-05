import json
import unittest
from pathlib import Path

from app.schemas.robot.auxiliary_sensors import (
    AuxiliarySensorsConfig,
    HTS221SensorConfig,
    LPS25HSensorConfig,
    LSM9DS1MagnetometerSensorConfig,
)
from app.schemas.robot.config import HardwareConfig
from pydantic import ValidationError


class TestAuxiliarySensorConfig(unittest.TestCase):
    def test_parses_complete_sense_hat_sensor_list(self) -> None:
        config = AuxiliarySensorsConfig.model_validate(
            {
                "sensors": [
                    {"driver": "hts221"},
                    {"driver": "lps25h"},
                    {"driver": "lsm9ds1_magnetometer"},
                ]
            }
        )

        self.assertIsInstance(config.sensors[0], HTS221SensorConfig)
        self.assertIsInstance(config.sensors[1], LPS25HSensorConfig)
        self.assertIsInstance(config.sensors[2], LSM9DS1MagnetometerSensorConfig)
        humidity = config.sensors[0]
        barometer = config.sensors[1]
        magnetometer = config.sensors[2]
        assert isinstance(humidity, HTS221SensorConfig)
        assert isinstance(barometer, LPS25HSensorConfig)
        assert isinstance(magnetometer, LSM9DS1MagnetometerSensorConfig)
        self.assertEqual(humidity.address_int, 0x5F)
        self.assertEqual(barometer.address_int, 0x5C)
        self.assertEqual(magnetometer.address_int, 0x1C)

    def test_rejects_invalid_addresses_names_and_duplicate_resources(self) -> None:
        with self.assertRaisesRegex(ValidationError, "HTS221 address"):
            HTS221SensorConfig(address="0x5e")
        with self.assertRaisesRegex(ValidationError, "names must be unique"):
            AuxiliarySensorsConfig.model_validate(
                {
                    "sensors": [
                        {"driver": "hts221", "name": "Cabin"},
                        {"driver": "lps25h", "name": " cabin "},
                    ]
                }
            )
        with self.assertRaisesRegex(ValidationError, "bus/address pairs"):
            AuxiliarySensorsConfig.model_validate(
                {
                    "sensors": [
                        {"driver": "lps25h", "name": "One"},
                        {"driver": "lps25h", "name": "Two"},
                    ]
                }
            )

    def test_rejects_polling_faster_than_hardware_output(self) -> None:
        with self.assertRaisesRegex(ValidationError, "poll rate"):
            HTS221SensorConfig(poll_interval_seconds=0.5)
        config = LSM9DS1MagnetometerSensorConfig(poll_interval_seconds=0.05)
        self.assertEqual(config.output_data_rate_hz.value, 20.0)

    def test_old_hardware_config_remains_valid_with_empty_default(self) -> None:
        data = json.loads(
            (Path(__file__).parents[4] / "config.json").read_text(encoding="utf-8")
        )
        data.pop("auxiliary_sensors", None)

        config = HardwareConfig.model_validate(data)

        self.assertEqual(config.auxiliary_sensors.sensors, [])

    def test_schema_exposes_discriminated_driver_options(self) -> None:
        schema = HardwareConfig.model_json_schema()
        auxiliary = schema["properties"]["auxiliary_sensors"]
        self.assertIn("AuxiliarySensorsConfig", auxiliary["$ref"])
        definitions = schema["$defs"]
        sensor_items = definitions["AuxiliarySensorsConfig"]["properties"]["sensors"][
            "items"
        ]
        self.assertEqual(
            definitions["AuxiliarySensorsConfig"]["properties"]["sensors"]["props"][
                "typeLabel"
            ],
            "Sensor type",
        )
        self.assertEqual(sensor_items["discriminator"]["propertyName"], "driver")
        self.assertEqual(
            set(sensor_items["discriminator"]["mapping"]),
            {
                "hts221",
                "lps25h",
                "lsm9ds1_magnetometer",
                "mock_environmental",
                "mock_magnetometer",
            },
        )
        self.assertEqual(
            definitions["HTS221SensorConfig"]["title"],
            "Sense HAT temperature and humidity (HTS221)",
        )
        self.assertEqual(
            definitions["LPS25HSensorConfig"]["title"],
            "Sense HAT pressure and temperature (LPS25H/HB)",
        )


if __name__ == "__main__":
    unittest.main()
