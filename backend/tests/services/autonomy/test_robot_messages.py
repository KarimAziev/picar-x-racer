import math
import unittest

from app.schemas.autonomy import (
    EncoderReading,
    EncoderState,
    ImuData,
    LaserScan,
    MessageHeader,
    Odometry2D,
    SteeringState,
)
from pydantic import ValidationError


class TestRobotMessages(unittest.TestCase):
    def header(self, frame_id: str = "base_link") -> MessageHeader:
        return MessageHeader(
            sequence=1,
            frame_id=frame_id,
            timestamp_monotonic_ns=1_000,
        )

    def test_header_requires_relative_frame_and_monotonic_timestamp(self) -> None:
        for frame_id in ["", " ", "/laser"]:
            with self.subTest(frame_id=frame_id):
                with self.assertRaises(ValidationError):
                    self.header(frame_id)
        with self.assertRaises(ValidationError):
            MessageHeader(
                sequence=0,
                frame_id="laser",
                timestamp_monotonic_ns=-1,
            )

    def test_laser_scan_allows_positive_infinity_but_rejects_nan(self) -> None:
        scan = LaserScan(
            header=self.header("laser"),
            angle_min_rad=-1.0,
            angle_max_rad=1.0,
            angle_increment_rad=0.5,
            range_min_m=0.1,
            range_max_m=12.0,
            ranges_m=(0.5, math.inf, 1.5),
        )
        self.assertTrue(math.isinf(scan.ranges_m[1]))

        with self.assertRaisesRegex(ValidationError, "non-negative"):
            LaserScan.model_validate({**scan.model_dump(), "ranges_m": (math.nan,)})

    def test_laser_scan_validates_bounds_and_parallel_intensities(self) -> None:
        params = {
            "header": self.header("laser"),
            "angle_min_rad": -1.0,
            "angle_max_rad": 1.0,
            "angle_increment_rad": 0.5,
            "range_min_m": 0.1,
            "range_max_m": 12.0,
            "ranges_m": (0.5, 1.0),
        }
        with self.assertRaisesRegex(ValidationError, "equal lengths"):
            LaserScan(**params, intensities=(1.0,))
        with self.assertRaisesRegex(ValidationError, "greater than range_min"):
            LaserScan(**{**params, "range_max_m": 0.1})

    def test_sensor_and_odometry_messages_use_explicit_si_fields(self) -> None:
        imu = ImuData(
            header=self.header("imu"),
            angular_velocity_z_radps=0.2,
            acceleration_x_mps2=0.1,
            acceleration_y_mps2=0.0,
            acceleration_z_mps2=9.81,
        )
        encoder = EncoderState(
            header=self.header(),
            left=EncoderReading(ticks=100, delta_ticks=5),
            right=EncoderReading(ticks=102, delta_ticks=7),
        )
        steering = SteeringState(
            header=self.header(),
            commanded_angle_rad=0.2,
        )
        odometry = Odometry2D(
            header=self.header("odom"),
            x_m=1.0,
            y_m=2.0,
            yaw_rad=0.3,
            linear_speed_mps=0.4,
            yaw_rate_radps=0.1,
        )

        self.assertEqual(imu.acceleration_z_mps2, 9.81)
        self.assertEqual(encoder.mean_delta_ticks, 6)
        self.assertIsNone(steering.measured_angle_rad)
        self.assertEqual(odometry.child_frame_id, "base_link")

    def test_messages_are_immutable(self) -> None:
        header = self.header()

        with self.assertRaises(ValidationError):
            setattr(header, "sequence", 2)


if __name__ == "__main__":
    unittest.main()
