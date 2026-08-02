import math
import unittest

from app.services.autonomy.steering_feedback import (
    SteeringAngleCalibration,
    SteeringCalibrationPoint,
)


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


if __name__ == "__main__":
    unittest.main()
