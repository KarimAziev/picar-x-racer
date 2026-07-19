import unittest

from app.schemas.robot.localization_sensors import (
    RPLidarC1SensorConfig,
    SH3001SensorConfig,
    StaticTransformConfig,
)
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


if __name__ == "__main__":
    unittest.main()
