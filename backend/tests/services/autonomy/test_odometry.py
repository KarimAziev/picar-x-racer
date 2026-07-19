import asyncio
import math
import unittest

from app.schemas.autonomy import EncoderState, MessageHeader, SteeringState
from app.schemas.robot.odometry import (
    AckermannOdometryConfig as AckermannOdometrySchema,
)
from app.services.autonomy import (
    AckermannOdometryConfig,
    AckermannOdometryEstimator,
    AckermannOdometryService,
    OdometryInputError,
    TopicBus,
)
from app.services.autonomy.topics import ENCODER_STATE, ODOMETRY, STEERING_STATE
from pydantic import ValidationError


class OdometryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.estimator = AckermannOdometryEstimator(
            AckermannOdometryConfig(
                wheelbase_m=0.2,
                max_steering_age_seconds=0.5,
            )
        )

    @staticmethod
    def encoder(
        sequence: int,
        timestamp_ns: int,
        *,
        delta_ticks: int = 0,
    ) -> EncoderState:
        return EncoderState(
            header=MessageHeader(
                sequence=sequence,
                frame_id="base_link",
                timestamp_monotonic_ns=timestamp_ns,
            ),
            ticks=delta_ticks,
            delta_ticks=delta_ticks,
            ticks_per_revolution=20,
            wheel_radius_m=0.1,
            gear_ratio=1.0,
        )

    @staticmethod
    def steering(
        timestamp_ns: int,
        commanded: float = 0.0,
        measured: float | None = None,
    ) -> SteeringState:
        return SteeringState(
            header=MessageHeader(
                sequence=1,
                frame_id="base_link",
                timestamp_monotonic_ns=timestamp_ns,
            ),
            commanded_angle_rad=commanded,
            measured_angle_rad=measured,
        )


class TestAckermannOdometryEstimator(OdometryTestCase):
    def test_runtime_config_requires_measured_geometry_when_enabled(self) -> None:
        self.assertFalse(AckermannOdometrySchema().enabled)
        with self.assertRaisesRegex(ValidationError, "requires calibrated"):
            AckermannOdometrySchema(enabled=True)

        config = AckermannOdometrySchema(
            enabled=True,
            wheelbase_m=0.2,
            wheel_radius_m=0.03,
            encoder_ticks_per_revolution=20,
            gear_ratio=2.0,
        )
        self.assertEqual(config.wheelbase_m, 0.2)

    def test_first_sample_establishes_time_without_inventing_motion(self) -> None:
        result = self.estimator.update(
            self.encoder(1, 1_000_000_000, delta_ticks=10),
            self.steering(1_000_000_000),
        )

        self.assertEqual(result.x_m, 0.0)
        self.assertEqual(result.linear_speed_mps, 0.0)

    def test_integrates_straight_signed_encoder_distance(self) -> None:
        self.estimator.update(
            self.encoder(1, 1_000_000_000),
            self.steering(1_000_000_000),
        )

        forward = self.estimator.update(
            self.encoder(2, 2_000_000_000, delta_ticks=20),
            self.steering(2_000_000_000),
        )
        reverse = self.estimator.update(
            self.encoder(3, 3_000_000_000, delta_ticks=-10),
            self.steering(3_000_000_000),
        )

        circumference = 2 * math.pi * 0.1
        self.assertAlmostEqual(forward.x_m, circumference)
        self.assertAlmostEqual(forward.linear_speed_mps, circumference)
        self.assertAlmostEqual(reverse.x_m, circumference / 2)
        self.assertAlmostEqual(reverse.linear_speed_mps, -circumference / 2)

    def test_bicycle_model_integrates_arc_at_midpoint_heading(self) -> None:
        self.estimator.update(
            self.encoder(1, 1_000_000_000),
            self.steering(1_000_000_000),
        )
        steering_angle = math.atan(0.2)

        result = self.estimator.update(
            self.encoder(2, 2_000_000_000, delta_ticks=20),
            self.steering(2_000_000_000, commanded=steering_angle),
        )

        distance = 2 * math.pi * 0.1
        expected_delta_yaw = distance
        self.assertAlmostEqual(result.yaw_rad, expected_delta_yaw)
        self.assertAlmostEqual(result.x_m, distance * math.cos(expected_delta_yaw / 2))
        self.assertAlmostEqual(result.y_m, distance * math.sin(expected_delta_yaw / 2))

    def test_measured_steering_takes_precedence_over_command(self) -> None:
        self.estimator.update(
            self.encoder(1, 1_000_000_000),
            self.steering(1_000_000_000),
        )

        result = self.estimator.update(
            self.encoder(2, 2_000_000_000, delta_ticks=20),
            self.steering(2_000_000_000, commanded=0.3, measured=0.0),
        )

        self.assertEqual(result.yaw_rad, 0.0)

    def test_rejects_stale_future_and_out_of_order_inputs(self) -> None:
        self.estimator.update(
            self.encoder(1, 1_000_000_000),
            self.steering(1_000_000_000),
        )

        with self.assertRaisesRegex(OdometryInputError, "stale"):
            self.estimator.update(
                self.encoder(2, 2_000_000_000),
                self.steering(1_000_000_000),
            )
        with self.assertRaisesRegex(OdometryInputError, "future"):
            self.estimator.update(
                self.encoder(3, 3_000_000_000),
                self.steering(3_000_000_001),
            )
        with self.assertRaisesRegex(OdometryInputError, "sequence"):
            self.estimator.update(
                self.encoder(1, 4_000_000_000),
                self.steering(4_000_000_000),
            )

    def test_gear_ratio_reduces_wheel_distance(self) -> None:
        self.estimator.update(
            self.encoder(1, 1_000_000_000),
            self.steering(1_000_000_000),
        )
        encoder = self.encoder(2, 2_000_000_000, delta_ticks=20).model_copy(
            update={"gear_ratio": 2.0}
        )

        result = self.estimator.update(encoder, self.steering(2_000_000_000))

        self.assertAlmostEqual(result.x_m, math.pi * 0.1)


class TestAckermannOdometryService(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.bus = TopicBus()
        self.estimator = AckermannOdometryEstimator(
            AckermannOdometryConfig(wheelbase_m=0.2)
        )
        self.service = AckermannOdometryService(self.bus, self.estimator)

    async def asyncTearDown(self) -> None:
        await self.service.stop()

    async def test_consumes_topics_and_publishes_odometry(self) -> None:
        output = self.bus.subscribe(ODOMETRY, replay_latest=False)
        self.bus.publish(
            STEERING_STATE,
            OdometryTestCase.steering(1_000_000_000),
        )
        self.service.start()

        self.bus.publish(
            ENCODER_STATE,
            OdometryTestCase.encoder(1, 1_000_000_000),
        )

        result = await asyncio.wait_for(output.get(), timeout=1)
        self.assertEqual(result.header.frame_id, "odom")
        self.assertEqual(result.child_frame_id, "base_link")
        self.assertEqual(self.service.published_updates, 1)

    async def test_skips_encoder_until_steering_is_available(self) -> None:
        self.service.start()

        self.bus.publish(
            ENCODER_STATE,
            OdometryTestCase.encoder(1, 1_000_000_000),
        )
        await asyncio.sleep(0)

        self.assertEqual(self.service.skipped_updates, 1)
        self.assertIsNone(self.bus.latest(ODOMETRY))


if __name__ == "__main__":
    unittest.main()
