import json
import unittest
from pathlib import Path

from app.schemas.robot.config import HardwareConfig
from app.schemas.robot.localization_sensors import (
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

        with self.assertRaisesRegex(ValidationError, "relative"):
            SH3001SensorConfig(frame_id="/imu")

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


if __name__ == "__main__":
    unittest.main()
