import asyncio
import math
import unittest

from app.services.autonomy.steering_feedback import (
    SteeringAngleCalibration,
    SteeringCalibrationPoint,
    SteeringFeedbackService,
)
from robot_hat import MockAngularPosition


class TestSteeringAngleCalibration(unittest.TestCase):
    def test_wraps_absolute_bearing_to_signed_wheel_angle(self) -> None:
        calibration = SteeringAngleCalibration(center_angle_deg=180.0)

        self.assertAlmostEqual(
            calibration.to_wheel_angle_rad(170.0),
            math.radians(-10.0),
        )
        self.assertAlmostEqual(
            calibration.to_wheel_angle_rad(190.0),
            math.radians(10.0),
        )

    def test_applies_direction_and_mechanical_ratio(self) -> None:
        calibration = SteeringAngleCalibration(
            center_angle_deg=5.0,
            invert_direction=True,
            wheel_degrees_per_sensor_degree=0.5,
        )

        self.assertAlmostEqual(
            calibration.to_wheel_angle_rad(355.0),
            math.radians(5.0),
        )

    def test_interpolates_asymmetric_linkage_calibration(self) -> None:
        calibration = SteeringAngleCalibration(
            center_angle_deg=180.0,
            points=(
                SteeringCalibrationPoint(-20.0, math.radians(-30.0)),
                SteeringCalibrationPoint(0.0, 0.0),
                SteeringCalibrationPoint(10.0, math.radians(25.0)),
            ),
        )

        self.assertAlmostEqual(
            calibration.to_wheel_angle_rad(185.0),
            math.radians(12.5),
        )
        with self.assertRaisesRegex(ValueError, "outside"):
            calibration.to_wheel_angle_rad(200.0)

    def test_rejects_ambiguous_or_unordered_calibration(self) -> None:
        with self.assertRaises(ValueError):
            SteeringAngleCalibration(
                center_angle_deg=0.0,
                points=(SteeringCalibrationPoint(0.0, 0.0),),
            )
        with self.assertRaises(ValueError):
            SteeringAngleCalibration(
                center_angle_deg=0.0,
                points=(
                    SteeringCalibrationPoint(1.0, 0.1),
                    SteeringCalibrationPoint(1.0, 0.2),
                ),
            )


class TestSteeringFeedbackService(unittest.IsolatedAsyncioTestCase):
    async def test_samples_and_calibrates_mock_position(self) -> None:
        sensor = MockAngularPosition(initial_angle_degrees=190.0)
        service = SteeringFeedbackService(
            lambda: sensor,
            SteeringAngleCalibration(center_angle_deg=180.0),
            sample_frequency_hz=100,
        )

        await service.start()
        try:
            for _attempt in range(20):
                if service.latest is not None:
                    break
                await asyncio.sleep(0.005)
            sample = service.latest
            self.assertIsNotNone(sample)
            assert sample is not None
            self.assertAlmostEqual(sample.wheel_angle_rad, math.radians(10.0))
            self.assertIsNone(service.last_error)
        finally:
            await service.stop()

        self.assertFalse(sensor.read_health().available)
        self.assertIsNone(service.latest)


if __name__ == "__main__":
    unittest.main()
