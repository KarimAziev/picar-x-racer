import json
import unittest
from pathlib import Path

from app.schemas.robot.config import HardwareConfig
from app.schemas.robot.localization_sensors import (
    EncoderSensorConfig,
    LocalizationSensorsConfig,
    LSM9DS1SensorConfig,
    MockIMUSensorConfig,
    MockLidarSensorConfig,
    MockSteeringPositionConfig,
    RPLidarC1SensorConfig,
    SH3001SensorConfig,
    StaticTransformConfig,
)
from app.schemas.robot.safety import LidarSafetyConfig
from pydantic import ValidationError


class TestLocalizationSensorConfig(unittest.TestCase):
    def test_lidar_requires_measured_range_only_when_enabled(self) -> None:
        self.assertFalse(RPLidarC1SensorConfig().enabled)

        with self.assertRaisesRegex(ValidationError, "range_min_m"):
            RPLidarC1SensorConfig(enabled=True)

        config = RPLidarC1SensorConfig(
            enabled=True,
            range_min_m=0.05,
            range_max_m=12.0,
        )
        self.assertEqual(config.frame_id, "laser")

    def test_imu_parses_hex_address_and_rejects_absolute_frame(self) -> None:
        self.assertEqual(SH3001SensorConfig(address="0x36").address_int, 0x36)
        self.assertEqual(LSM9DS1SensorConfig(address="0x6a").address_int, 0x6A)

        with self.assertRaisesRegex(ValidationError, "relative"):
            SH3001SensorConfig(frame_id="/imu")

    def test_lsm9ds1_output_rate_covers_publisher_sample_rate(self) -> None:
        config = LSM9DS1SensorConfig(
            sample_frequency_hz=200,
            output_data_rate_hz=238,
        )
        self.assertEqual(config.gyroscope_range_dps, 245)

        with self.assertRaisesRegex(ValidationError, "output_data_rate_hz"):
            LSM9DS1SensorConfig(
                sample_frequency_hz=200,
                output_data_rate_hz=119,
            )

        with self.assertRaisesRegex(ValidationError, "0x6A or 0x6B"):
            LSM9DS1SensorConfig(address="0x36")

    def test_mock_sensors_have_useful_hardware_free_defaults(self) -> None:
        lidar = MockLidarSensorConfig(enabled=True)
        imu = MockIMUSensorConfig(enabled=True)
        steering = MockSteeringPositionConfig(enabled=True)

        self.assertEqual(lidar.distance_m, 2.0)
        self.assertEqual(lidar.range_max_m, 12.0)
        self.assertEqual(imu.acceleration_mps2, (0.0, 0.0, 9.80665))
        self.assertEqual(steering.initial_angle_degrees, 0.0)

    def test_drive_encoders_require_unique_sides_and_spi_devices(self) -> None:
        valid = EncoderSensorConfig.model_validate(
            {
                "enabled": True,
                "sensors": [
                    {"side": "left", "driver": "as5048a", "device": 0},
                    {"side": "right", "driver": "as5048a", "device": 1},
                ],
            }
        )
        self.assertEqual(len(valid.sensors), 2)

        with self.assertRaisesRegex(ValidationError, "sides must be unique"):
            EncoderSensorConfig.model_validate(
                {
                    "enabled": True,
                    "sensors": [
                        {"side": "left", "driver": "mock"},
                        {"side": "left", "driver": "mock"},
                    ],
                }
            )
        with self.assertRaisesRegex(ValidationError, "SPI bus/device"):
            EncoderSensorConfig.model_validate(
                {
                    "enabled": True,
                    "sensors": [
                        {"side": "left", "driver": "as5048a"},
                        {"side": "right", "driver": "as5048a"},
                    ],
                }
            )

    def test_enabled_as5048a_sensors_cannot_share_chip_select(self) -> None:
        root_config = Path(__file__).parents[4] / "config.json"
        with self.assertRaisesRegex(ValidationError, "unique SPI"):
            HardwareConfig.model_validate(
                {
                    **json.loads(root_config.read_text()),
                    "localization_sensors": {
                        "lidar": {"driver": "rplidar_c1"},
                        "imu": {"driver": "sh3001"},
                        "encoder": {
                            "enabled": True,
                            "sensors": [
                                {
                                    "side": "left",
                                    "driver": "as5048a",
                                    "bus": 0,
                                    "device": 0,
                                }
                            ],
                        },
                        "steering": {
                            "enabled": True,
                            "driver": "as5048a",
                            "bus": 0,
                            "device": 0,
                        },
                    },
                }
            )

    def test_as5600l_and_gpio_quadrature_resources_must_be_unique(self) -> None:
        with self.assertRaisesRegex(ValidationError, "AS5600L"):
            EncoderSensorConfig.model_validate(
                {
                    "enabled": True,
                    "sensors": [
                        {"side": "left", "driver": "as5600l"},
                        {"side": "right", "driver": "as5600l"},
                    ],
                }
            )

        with self.assertRaisesRegex(ValidationError, "unique A/B"):
            EncoderSensorConfig.model_validate(
                {
                    "enabled": True,
                    "sensors": [
                        {
                            "side": "left",
                            "driver": "gpio_quadrature",
                            "a_pin": 17,
                            "b_pin": 27,
                        },
                        {
                            "side": "right",
                            "driver": "gpio_quadrature",
                            "a_pin": 22,
                            "b_pin": 27,
                        },
                    ],
                }
            )

        with self.assertRaisesRegex(ValidationError, "unique bus/address"):
            LocalizationSensorsConfig.model_validate(
                {
                    "imu": {"enabled": False, "driver": "sh3001"},
                    "encoder": {
                        "enabled": True,
                        "sensors": [
                            {
                                "side": "left",
                                "driver": "as5600l",
                                "bus": 1,
                                "address": "0x40",
                            }
                        ],
                    },
                    "steering": {
                        "enabled": True,
                        "driver": "as5600l",
                        "bus": 1,
                        "address": "0x40",
                    },
                }
            )

    def test_schema_exposes_every_robot_hat_encoder_and_position_driver(self) -> None:
        schema = json.dumps(LocalizationSensorsConfig.model_json_schema())

        for driver in ("as5048a", "as5600l", "gpio_quadrature", "mock"):
            self.assertIn(f'"{driver}"', schema)

    def test_schema_exposes_every_robot_hat_imu_driver(self) -> None:
        schema = json.dumps(LocalizationSensorsConfig.model_json_schema())

        for driver in ("sh3001", "lsm9ds1", "mock"):
            self.assertIn(f'"{driver}"', schema)

    def test_transform_rejects_non_finite_measurements(self) -> None:
        with self.assertRaises(ValidationError):
            StaticTransformConfig(x_m=float("nan"))

    def test_lidar_safety_requires_measured_stop_and_slow_distances(self) -> None:
        self.assertFalse(LidarSafetyConfig().enabled)

        with self.assertRaisesRegex(ValidationError, "stop_distance_m"):
            LidarSafetyConfig(enabled=True)

        config = LidarSafetyConfig(
            enabled=True,
            stop_distance_m=0.3,
            slow_distance_m=1.0,
        )
        self.assertEqual(config.min_obstacle_points, 2)

    def test_lidar_safety_requires_motion_control_and_lidar_publisher(self) -> None:
        root_config = Path(__file__).parents[4] / "config.json"
        data = json.loads(root_config.read_text())
        data["lidar_safety"] = {
            "enabled": True,
            "stop_distance_m": 0.3,
            "slow_distance_m": 1.0,
        }

        with self.assertRaisesRegex(ValidationError, "motion control"):
            HardwareConfig.model_validate(data)

        data["motion_control"].update(
            enabled=True,
            max_forward_speed_mps=1.0,
            max_reverse_speed_mps=0.5,
        )
        with self.assertRaisesRegex(ValidationError, "LiDAR publisher"):
            HardwareConfig.model_validate(data)

        data["localization_sensors"]["lidar"].update(
            enabled=True,
            range_min_m=0.05,
            range_max_m=12.0,
        )
        config = HardwareConfig.model_validate(data)
        self.assertTrue(config.lidar_safety.enabled)

    def test_local_mapping_requires_odometry_and_lidar(self) -> None:
        root_config = Path(__file__).parents[4] / "config.json"
        data = json.loads(root_config.read_text())
        data["local_mapping"] = {"enabled": True}

        with self.assertRaisesRegex(ValidationError, "Ackermann odometry"):
            HardwareConfig.model_validate(data)

        data["ackermann_odometry"].update(
            enabled=True,
            wheelbase_m=0.2,
            wheel_radius_m=0.03,
            encoder_ticks_per_revolution=20,
        )
        data["motion_control"].update(
            enabled=True,
            max_forward_speed_mps=1.0,
            max_reverse_speed_mps=0.5,
        )
        data["localization_sensors"]["encoder"] = {
            "enabled": True,
            "sensors": [{"side": "left", "driver": "mock"}],
        }
        with self.assertRaisesRegex(ValidationError, "LiDAR publisher"):
            HardwareConfig.model_validate(data)

        data["localization_sensors"]["lidar"].update(
            enabled=True,
            range_min_m=0.05,
            range_max_m=12.0,
        )
        config = HardwareConfig.model_validate(data)
        self.assertTrue(config.local_mapping.enabled)

    def test_odometry_validates_known_magnetic_encoder_resolution(self) -> None:
        root_config = Path(__file__).parents[4] / "config.json"
        data = json.loads(root_config.read_text())
        data["motion_control"].update(
            enabled=True,
            max_forward_speed_mps=1.0,
            max_reverse_speed_mps=0.5,
        )
        data["ackermann_odometry"].update(
            enabled=True,
            wheelbase_m=0.2,
            wheel_radius_m=0.03,
            encoder_ticks_per_revolution=16_384,
        )
        data["localization_sensors"]["encoder"] = {
            "enabled": True,
            "sensors": [{"side": "left", "driver": "as5600l"}],
        }

        with self.assertRaisesRegex(ValidationError, "must be 4096"):
            HardwareConfig.model_validate(data)

        data["ackermann_odometry"]["encoder_ticks_per_revolution"] = 4_096
        config = HardwareConfig.model_validate(data)
        self.assertTrue(config.ackermann_odometry.enabled)


if __name__ == "__main__":
    unittest.main()
