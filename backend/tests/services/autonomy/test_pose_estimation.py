import asyncio
import math
import unittest

from app.schemas.autonomy import (
    ImuData,
    MessageHeader,
    Odometry2D,
    PoseObservation2D,
)
from app.services.autonomy import (
    PoseEstimationInputError,
    PoseEstimator,
    PoseEstimatorConfig,
    PoseEstimatorService,
    PoseEstimatorSupervisor,
    TopicBus,
)
from app.services.autonomy.topics import (
    IMU_DATA,
    LOCALIZATION_POSE,
    ODOMETRY,
    POSE_OBSERVATION,
)


def odometry(
    sequence: int,
    timestamp_ns: int,
    *,
    x_m: float = 0,
    y_m: float = 0,
    yaw_rad: float = 0,
    linear_speed_mps: float = 0,
    yaw_rate_radps: float = 0,
) -> Odometry2D:
    return Odometry2D(
        header=MessageHeader(
            sequence=sequence,
            frame_id="odom",
            timestamp_monotonic_ns=timestamp_ns,
        ),
        x_m=x_m,
        y_m=y_m,
        yaw_rad=yaw_rad,
        linear_speed_mps=linear_speed_mps,
        yaw_rate_radps=yaw_rate_radps,
    )


def imu(timestamp_ns: int, yaw_rate_radps: float) -> ImuData:
    return ImuData(
        header=MessageHeader(
            sequence=1,
            frame_id="imu",
            timestamp_monotonic_ns=timestamp_ns,
        ),
        angular_velocity_z_radps=yaw_rate_radps,
        acceleration_x_mps2=0,
        acceleration_y_mps2=0,
        acceleration_z_mps2=9.81,
    )


def observation(
    timestamp_ns: int,
    *,
    x_m: float,
    y_m: float,
    yaw_rad: float,
    frame_id: str = "odom",
) -> PoseObservation2D:
    return PoseObservation2D(
        header=MessageHeader(
            sequence=1,
            frame_id=frame_id,
            timestamp_monotonic_ns=timestamp_ns,
        ),
        x_m=x_m,
        y_m=y_m,
        yaw_rad=yaw_rad,
        position_variance_m2=0.01,
        yaw_variance_rad2=0.01,
        source="test_localizer",
    )


class TestPoseEstimator(unittest.TestCase):
    def test_first_odometry_sample_initializes_without_inventing_motion(self) -> None:
        estimator = PoseEstimator(PoseEstimatorConfig())

        result = estimator.update(
            odometry(1, 1_000_000_000, x_m=1.2, y_m=-0.3, yaw_rad=0.4),
            imu=imu(1_000_000_000, 2),
        )

        self.assertEqual(result.pose.x_m, 1.2)
        self.assertEqual(result.pose.y_m, -0.3)
        self.assertEqual(result.pose.yaw_rad, 0.4)
        self.assertFalse(result.imu_used)
        self.assertEqual(result.pose.fusion_mode, "wheel")

    def test_blends_fresh_gyro_and_wheel_heading_increments(self) -> None:
        estimator = PoseEstimator(PoseEstimatorConfig(imu_yaw_rate_weight=0.25))
        estimator.update(odometry(1, 1_000_000_000))

        result = estimator.update(
            odometry(
                2,
                2_000_000_000,
                x_m=math.cos(0.2),
                y_m=math.sin(0.2),
                yaw_rad=0.4,
                linear_speed_mps=1,
                yaw_rate_radps=0.4,
            ),
            imu=imu(2_000_000_000, 0.8),
        )

        expected_yaw = 0.75 * 0.4 + 0.25 * 0.8
        self.assertTrue(result.imu_used)
        self.assertEqual(result.pose.fusion_mode, "wheel_imu")
        self.assertAlmostEqual(result.pose.yaw_rad, expected_yaw)
        self.assertAlmostEqual(result.pose.x_m, math.cos(expected_yaw / 2))
        self.assertAlmostEqual(result.pose.y_m, math.sin(expected_yaw / 2))

    def test_rejects_stale_and_future_imu_without_dropping_odometry(self) -> None:
        estimator = PoseEstimator(PoseEstimatorConfig(max_imu_age_seconds=0.1))
        estimator.update(odometry(1, 1_000_000_000))

        stale = estimator.update(
            odometry(2, 2_000_000_000, yaw_rad=0.2),
            imu=imu(1_000_000_000, 1),
        )
        future = estimator.update(
            odometry(3, 3_000_000_000, yaw_rad=0.4),
            imu=imu(3_000_000_001, 1),
        )

        self.assertEqual(stale.imu_rejection, "IMU observation is stale")
        self.assertEqual(future.imu_rejection, "IMU observation is from the future")
        self.assertAlmostEqual(future.pose.yaw_rad, 0.4)

    def test_pose_delta_preserves_distance_across_skipped_odometry(self) -> None:
        estimator = PoseEstimator(PoseEstimatorConfig())
        estimator.update(odometry(1, 1_000_000_000))

        result = estimator.update(
            odometry(
                50,
                5_000_000_000,
                x_m=1,
                linear_speed_mps=0.1,
            )
        )

        self.assertAlmostEqual(result.pose.x_m, 1)

    def test_pose_observation_reduces_error_and_uncertainty(self) -> None:
        estimator = PoseEstimator(
            PoseEstimatorConfig(
                initial_position_stddev_m=1,
                initial_heading_stddev_rad=1,
            )
        )
        estimator.update(odometry(1, 1_000_000_000))

        result = estimator.update(
            odometry(2, 2_000_000_000),
            observation=observation(
                2_000_000_000,
                x_m=1,
                y_m=-1,
                yaw_rad=0.5,
            ),
        )

        self.assertTrue(result.correction_applied)
        self.assertEqual(result.pose.fusion_mode, "corrected")
        self.assertEqual(result.pose.last_correction_source, "test_localizer")
        self.assertGreater(result.pose.x_m, 0.9)
        self.assertLess(result.pose.position_variance_m2, 0.01)
        self.assertLess(result.pose.yaw_variance_rad2, 0.01)
        self.assertAlmostEqual(result.position_innovation_m or 0, math.sqrt(2))

    def test_rejects_wrong_frame_and_replayed_observation(self) -> None:
        estimator = PoseEstimator(PoseEstimatorConfig())
        estimator.update(odometry(1, 1_000_000_000))
        wrong_frame = estimator.update(
            odometry(2, 2_000_000_000),
            observation=observation(
                2_000_000_000,
                x_m=0,
                y_m=0,
                yaw_rad=0,
                frame_id="map",
            ),
        )
        valid_observation = observation(
            3_000_000_000,
            x_m=0,
            y_m=0,
            yaw_rad=0,
        )
        estimator.update(
            odometry(3, 3_000_000_000),
            observation=valid_observation,
        )
        replay = estimator.update(
            odometry(4, 3_100_000_000),
            observation=valid_observation,
        )

        self.assertIn("frame", wrong_frame.correction_rejection or "")
        self.assertIn("increase", replay.correction_rejection or "")

    def test_rejects_non_monotonic_odometry(self) -> None:
        estimator = PoseEstimator(PoseEstimatorConfig())
        estimator.update(odometry(1, 1_000_000_000))

        with self.assertRaisesRegex(PoseEstimationInputError, "sequence"):
            estimator.update(odometry(1, 2_000_000_000))


class TestPoseEstimatorService(unittest.IsolatedAsyncioTestCase):
    async def test_consumes_topics_publishes_pose_and_tracks_input_use(self) -> None:
        bus = TopicBus()
        service = PoseEstimatorService(
            bus,
            PoseEstimator(PoseEstimatorConfig(imu_yaw_rate_weight=0.5)),
        )
        output = bus.subscribe(LOCALIZATION_POSE, replay_latest=False)
        service.start()
        try:
            bus.publish(IMU_DATA, imu(1_000_000_000, 0.2))
            bus.publish(ODOMETRY, odometry(1, 1_000_000_000))
            first = await asyncio.wait_for(output.get(), timeout=1)
            bus.publish(IMU_DATA, imu(2_000_000_000, 0.2))
            bus.publish(
                POSE_OBSERVATION,
                observation(
                    2_000_000_000,
                    x_m=0.1,
                    y_m=0,
                    yaw_rad=0.1,
                ),
            )
            await asyncio.sleep(0)
            bus.publish(
                ODOMETRY,
                odometry(
                    2,
                    2_000_000_000,
                    x_m=0.1,
                    yaw_rad=0.1,
                    linear_speed_mps=0.1,
                ),
            )
            second = await asyncio.wait_for(output.get(), timeout=1)
        finally:
            output.close()
            await service.stop()

        self.assertEqual(first.header.frame_id, "odom")
        self.assertEqual(second.fusion_mode, "corrected")
        self.assertEqual(service.published_updates, 2)
        self.assertEqual(service.imu_updates_used, 1)
        self.assertEqual(service.corrections_applied, 1)

    async def test_keeps_future_observation_until_odometry_reaches_it(self) -> None:
        bus = TopicBus()
        service = PoseEstimatorService(bus, PoseEstimator(PoseEstimatorConfig()))
        service.start()
        try:
            bus.publish(
                POSE_OBSERVATION,
                observation(2_000_000_000, x_m=1, y_m=0, yaw_rad=0),
            )
            await asyncio.sleep(0)
            bus.publish(ODOMETRY, odometry(1, 1_000_000_000))
            await asyncio.sleep(0)
            self.assertEqual(service.corrections_rejected, 0)
            bus.publish(ODOMETRY, odometry(2, 2_000_000_000))
            await asyncio.sleep(0)
            self.assertEqual(service.corrections_applied, 1)
        finally:
            await service.stop()

    async def test_supervisor_hot_reconfigures_and_resets(self) -> None:
        bus = TopicBus()
        first = PoseEstimatorService(bus, PoseEstimator(PoseEstimatorConfig()))
        second = PoseEstimatorService(
            bus,
            PoseEstimator(PoseEstimatorConfig(imu_yaw_rate_weight=0.75)),
        )
        supervisor = PoseEstimatorSupervisor(first)
        await supervisor.start()
        try:
            await supervisor.reconfigure(second)
            self.assertIs(supervisor.service, second)
            self.assertTrue(second.running)
            await supervisor.reset()
            self.assertEqual(second.published_updates, 0)
        finally:
            await supervisor.stop()


if __name__ == "__main__":
    unittest.main()
