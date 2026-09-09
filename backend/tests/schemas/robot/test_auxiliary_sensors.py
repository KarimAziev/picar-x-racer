import json
import unittest
from pathlib import Path

from app.schemas.robot.auxiliary_sensors import (
    AuxiliarySensorsConfig,
    HTS221SensorConfig,
    LIS3MDLOutputDataRate,
    LIS3MDLSensorConfig,
    LPS25HSensorConfig,
    LSM9DS1MagnetometerSensorConfig,
)
from app.schemas.robot.config import HardwareConfig
from app.schemas.robot.localization_sensors import LSM6DS33SensorConfig
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

    def test_parses_both_miniimu9_v5_components(self) -> None:
        data = json.loads(
            (Path(__file__).parents[4] / "config.json").read_text(encoding="utf-8")
        )
        data["localization_sensors"]["imu"] = {
            "enabled": True,
            "driver": "lsm6ds33",
        }
        data["auxiliary_sensors"] = {"sensors": [{"driver": "lis3mdl"}]}

        config = HardwareConfig.model_validate(data)

        imu = config.localization_sensors.imu
        magnetometer = config.auxiliary_sensors.sensors[0]
        assert isinstance(imu, LSM6DS33SensorConfig)
        assert isinstance(magnetometer, LIS3MDLSensorConfig)
        self.assertTrue(imu.enabled)
        self.assertTrue(magnetometer.enabled)
        self.assertEqual((imu.bus, magnetometer.bus), (1, 1))
        self.assertEqual((imu.address_int, magnetometer.address_int), (0x6B, 0x1E))
        self.assertEqual(magnetometer.name, "LIS3MDL")
        self.assertEqual(magnetometer.magnetic_field_range_gauss, 4)
        self.assertEqual(magnetometer.output_data_rate_hz, LIS3MDLOutputDataRate.HZ_10)
        self.assertEqual(magnetometer.performance_mode, "ultra_high")

    def test_lis3mdl_validates_addresses_and_hardware_settings(self) -> None:
        for address in (0x1C, 0x1E, "0x1c", "0x1e"):
            with self.subTest(address=address):
                config = LIS3MDLSensorConfig(address=address)
                self.assertEqual(
                    config.address_int,
                    int(address, 16) if isinstance(address, str) else address,
                )
        for address in ("0x6b", "not-an-address"):
            with self.subTest(address=address):
                with self.assertRaisesRegex(ValidationError, "LIS3MDL.*address"):
                    LIS3MDLSensorConfig(address=address)

        invalid_settings = (
            {"magnetic_field_range_gauss": 2},
            {"output_data_rate_hz": 100},
            {"performance_mode": "maximum"},
        )
        for settings in invalid_settings:
            with self.subTest(settings=settings):
                with self.assertRaises(ValidationError):
                    LIS3MDLSensorConfig.model_validate(settings)

    def test_lis3mdl_poll_rate_matches_integer_and_fractional_output(self) -> None:
        for rate in LIS3MDLOutputDataRate:
            with self.subTest(rate=rate.value):
                config = LIS3MDLSensorConfig(
                    output_data_rate_hz=rate,
                    poll_interval_seconds=max(0.05, 1.0 / rate.value),
                )
                self.assertEqual(config.output_data_rate_hz, rate)
        for rate, interval in (
            (LIS3MDLOutputDataRate.HZ_0_625, 1.59),
            (LIS3MDLOutputDataRate.HZ_10, 0.05),
        ):
            with self.subTest(rate=rate.value, interval=interval):
                with self.assertRaisesRegex(ValidationError, "LIS3MDL.*poll rate"):
                    LIS3MDLSensorConfig(
                        output_data_rate_hz=rate, poll_interval_seconds=interval
                    )

    def test_lis3mdl_conflicts_only_with_enabled_same_bus_address(self) -> None:
        for driver in ("lis3mdl", "lsm9ds1_magnetometer"):
            with self.subTest(driver=driver):
                with self.assertRaisesRegex(ValidationError, "bus/address pairs"):
                    AuxiliarySensorsConfig.model_validate(
                        {
                            "sensors": [
                                {"driver": "lis3mdl", "name": "One"},
                                {"driver": driver, "name": "Two", "address": 0x1E},
                            ]
                        }
                    )
        for alternate in (
            {"address": "0x1c"},
            {"bus": 2},
            {"enabled": False},
        ):
            with self.subTest(alternate=alternate):
                config = AuxiliarySensorsConfig.model_validate(
                    {
                        "sensors": [
                            {"driver": "lis3mdl", "name": "One"},
                            {"driver": "lis3mdl", "name": "Two", **alternate},
                        ]
                    }
                )
                self.assertEqual(len(config.sensors), 2)

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
                "lis3mdl",
                "lps25h",
                "lsm9ds1_magnetometer",
                "mock_environmental",
                "mock_magnetometer",
            },
        )
        self.assertEqual(
            definitions["HTS221SensorConfig"]["title"],
            "Temperature/humidity (HTS221)",
        )
        self.assertEqual(
            definitions["LPS25HSensorConfig"]["title"],
            "Pressure and temperature (LPS25H/HB)",
        )
        self.assertEqual(
            definitions["LIS3MDLSensorConfig"]["title"],
            "LIS3MDL (magnetometer)",
        )
        self.assertEqual(
            definitions["LSM6DS33SensorConfig"]["title"],
            "LSM6DS33 (gyro and accelerometer)",
        )

    def test_schema_exposes_human_readable_sensor_field_metadata(self) -> None:
        definitions = HardwareConfig.model_json_schema()["$defs"]
        sensor_list = definitions["AuxiliarySensorsConfig"]["properties"]["sensors"]
        self.assertEqual(sensor_list["title"], "Auxiliary sensors")
        self.assertIn("Environmental and magnetic", sensor_list["description"])

        expected_fields = {
            "HTS221SensorConfig": {
                "name",
                "enabled",
                "poll_interval_seconds",
                "bus",
                "address",
                "driver",
                "output_data_rate_hz",
                "humidity_average_samples",
                "temperature_average_samples",
            },
            "LPS25HSensorConfig": {
                "name",
                "enabled",
                "poll_interval_seconds",
                "bus",
                "address",
                "driver",
                "output_data_rate_hz",
            },
            "LSM9DS1MagnetometerSensorConfig": {
                "name",
                "enabled",
                "poll_interval_seconds",
                "bus",
                "address",
                "driver",
                "magnetic_field_range_gauss",
                "output_data_rate_hz",
                "performance_mode",
            },
            "LIS3MDLSensorConfig": {
                "name",
                "enabled",
                "poll_interval_seconds",
                "bus",
                "address",
                "driver",
                "magnetic_field_range_gauss",
                "output_data_rate_hz",
                "performance_mode",
            },
            "MockEnvironmentalSensorConfig": {
                "name",
                "enabled",
                "poll_interval_seconds",
                "driver",
                "temperature_c",
                "relative_humidity_percent",
                "pressure_pa",
            },
            "MockMagnetometerSensorConfig": {
                "name",
                "enabled",
                "poll_interval_seconds",
                "driver",
                "magnetic_field_t",
            },
        }
        for model_name, field_names in expected_fields.items():
            with self.subTest(model=model_name):
                model_schema = definitions[model_name]
                self.assertTrue(model_schema.get("description"))
                for field_name in field_names:
                    with self.subTest(model=model_name, field=field_name):
                        field_schema = model_schema["properties"][field_name]
                        self.assertTrue(field_schema.get("title"))
                        self.assertTrue(field_schema.get("description"))

        hts221 = definitions["HTS221SensorConfig"]["properties"]
        self.assertEqual(hts221["name"]["title"], "Sensor name")
        self.assertTrue(hts221["name"]["shared"])
        self.assertEqual(hts221["poll_interval_seconds"]["title"], "Telemetry interval")
        self.assertTrue(hts221["poll_interval_seconds"]["shared"])
        self.assertTrue(hts221["bus"]["shared"])
        self.assertEqual(hts221["address"]["x-ui-type"], "hex")
        self.assertEqual(hts221["output_data_rate_hz"]["title"], "Output data rate")

        lis3mdl = definitions["LIS3MDLSensorConfig"]["properties"]
        self.assertTrue(lis3mdl["bus"]["shared"])
        self.assertEqual(lis3mdl["address"]["x-ui-type"], "hex")
        self.assertEqual(lis3mdl["address"]["default"], "0x1e")
        self.assertEqual(lis3mdl["output_data_rate_hz"]["default"], 10.0)


if __name__ == "__main__":
    unittest.main()
