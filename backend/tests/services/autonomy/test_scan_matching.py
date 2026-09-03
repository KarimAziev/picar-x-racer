import asyncio
import math
import unittest

from app.schemas.autonomy import (
    LaserScan,
    LocalizationPose2D,
    MessageHeader,
    Odometry2D,
)
from app.services.autonomy import (
    KnownWorldScanMatcher,
    KnownWorldScanMatcherConfig,
    KnownWorldScanMatcherService,
    PoseEstimator,
    PoseEstimatorConfig,
    RaycastLidarConfig,
    StaticTransform2D,
    TopicBus,
    WorldLidarRaycaster,
    build_simulation_world,
)
from app.services.autonomy.topics import (
    LIDAR_SCAN,
    LOCALIZATION_POSE,
    POSE_OBSERVATION,
)


def pose(
    x_m: float,
    y_m: float,
    yaw_rad: float,
    *,
    timestamp_ns: int = 990_000_000,
) -> LocalizationPose2D:
    return LocalizationPose2D(
        header=MessageHeader(
            sequence=1,
            frame_id="odom",
            timestamp_monotonic_ns=timestamp_ns,
        ),
        x_m=x_m,
        y_m=y_m,
        yaw_rad=yaw_rad,
        linear_speed_mps=0,
        yaw_rate_radps=0,
        position_variance_m2=0.25,
        yaw_variance_rad2=0.25,
        fusion_mode="wheel",
    )


class ScanMatchingFixture:
    def setUp(self) -> None:
        self.world = build_simulation_world("single_obstacle", width_m=6, height_m=6)
        self.sensor_transform = StaticTransform2D(0.08, 0.01, 0.02)
        self.raycaster = WorldLidarRaycaster(
            self.world,
            RaycastLidarConfig(
                frame_id="laser",
                sensor_x_m=self.sensor_transform.x_m,
                sensor_y_m=self.sensor_transform.y_m,
                sensor_yaw_rad=self.sensor_transform.yaw_rad,
                range_min_m=0.05,
                range_max_m=12,
                angular_resolution_deg=1,
            ),
        )
        self.matcher = KnownWorldScanMatcher(
            self.world,
            KnownWorldScanMatcherConfig(
                odom_origin_in_world=(0, 0, 0),
                sensor_transform=self.sensor_transform,
                expected_scan_frame_id="laser",
            ),
        )

    def scan(
        self,
        x_m: float = 0.8,
        y_m: float = 0.3,
        yaw_rad: float = 0.25,
    ) -> LaserScan:
        return self.raycaster.scan(
            base_x_m=x_m,
            base_y_m=y_m,
            base_yaw_rad=yaw_rad,
            timestamp_ns=1_000_000_000,
            sequence=1,
        )


class TestKnownWorldScanMatcher(ScanMatchingFixture, unittest.TestCase):
    def test_recovers_position_and_heading_without_simulator_truth_input(self) -> None:
        result = self.matcher.match(
            self.scan(),
            pose(0.9, 0.23, 0.31),
            sequence=4,
        )

        self.assertTrue(result.accepted)
        observation = result.observation
        self.assertIsNotNone(observation)
        self.assertAlmostEqual(observation.x_m, 0.8, delta=0.011)  # type: ignore[union-attr]
        self.assertAlmostEqual(observation.y_m, 0.3, delta=0.011)  # type: ignore[union-attr]
        self.assertAlmostEqual(observation.yaw_rad, 0.25, delta=0.01)  # type: ignore[union-attr]
        self.assertLess(result.mean_error_m or 1, result.prior_mean_error_m or 0)
        self.assertEqual(observation.header.sequence, 4)  # type: ignore[union-attr]

    def test_accounts_for_nonzero_odom_origin_and_sensor_transform(self) -> None:
        origin = (0.4, -0.2, 0.3)
        odom_truth = (0.35, 0.15, -0.1)
        world_x = (
            origin[0]
            + math.cos(origin[2]) * odom_truth[0]
            - math.sin(origin[2]) * odom_truth[1]
        )
        world_y = (
            origin[1]
            + math.sin(origin[2]) * odom_truth[0]
            + math.cos(origin[2]) * odom_truth[1]
        )
        scan = self.scan(world_x, world_y, origin[2] + odom_truth[2])
        matcher = KnownWorldScanMatcher(
            self.world,
            KnownWorldScanMatcherConfig(
                odom_origin_in_world=origin,
                sensor_transform=self.sensor_transform,
                expected_scan_frame_id="laser",
            ),
        )

        result = matcher.match(scan, pose(0.42, 0.08, -0.04), sequence=1)

        self.assertAlmostEqual(result.observation.x_m, odom_truth[0], delta=0.011)  # type: ignore[union-attr]
        self.assertAlmostEqual(result.observation.y_m, odom_truth[1], delta=0.011)  # type: ignore[union-attr]
        self.assertAlmostEqual(result.observation.yaw_rad, odom_truth[2], delta=0.01)  # type: ignore[union-attr]

    def test_repeated_match_is_deterministic(self) -> None:
        scan = self.scan()
        prior = pose(0.9, 0.23, 0.31)

        first = self.matcher.match(scan, prior, sequence=7)
        second = self.matcher.match(scan, prior, sequence=7)

        self.assertEqual(first, second)

    def test_rejects_insufficient_returns_and_bad_alignment(self) -> None:
        scan = self.scan()
        sparse = scan.model_copy(
            update={
                "ranges_m": tuple([1.0] * 2 + [math.inf] * (len(scan.ranges_m) - 2))
            }
        )
        insufficient = self.matcher.match(sparse, pose(0.8, 0.3, 0.25), sequence=1)
        bad = scan.model_copy(update={"ranges_m": tuple(0.35 for _ in scan.ranges_m)})
        poor = self.matcher.match(bad, pose(0.8, 0.3, 0.25), sequence=2)

        self.assertEqual(insufficient.rejection, "insufficient_points")
        self.assertEqual(poor.rejection, "poor_quality")

    def test_scan_correction_reduces_fused_pose_error(self) -> None:
        prior = pose(0.9, 0.23, 0.31)
        match = self.matcher.match(self.scan(), prior, sequence=1)
        estimator = PoseEstimator(
            PoseEstimatorConfig(
                initial_position_stddev_m=1,
                initial_heading_stddev_rad=1,
            )
        )
        first_odom = Odometry2D(
            header=prior.header,
            x_m=prior.x_m,
            y_m=prior.y_m,
            yaw_rad=prior.yaw_rad,
            linear_speed_mps=0,
            yaw_rate_radps=0,
        )
        estimator.update(first_odom)
        corrected = estimator.update(
            first_odom.model_copy(
                update={
                    "header": first_odom.header.model_copy(
                        update={"sequence": 2, "timestamp_monotonic_ns": 1_000_000_000}
                    )
                }
            ),
            observation=match.observation,
        ).pose

        prior_error = math.hypot(prior.x_m - 0.8, prior.y_m - 0.3)
        corrected_error = math.hypot(corrected.x_m - 0.8, corrected.y_m - 0.3)
        self.assertLess(corrected_error, prior_error * 0.1)
        self.assertEqual(corrected.fusion_mode, "corrected")


class TestKnownWorldScanMatcherService(
    ScanMatchingFixture, unittest.IsolatedAsyncioTestCase
):
    async def test_publishes_observation_and_tracks_quality(self) -> None:
        bus = TopicBus()
        service = KnownWorldScanMatcherService(
            bus, self.matcher, max_pose_age_seconds=0.2
        )
        output = bus.subscribe(POSE_OBSERVATION, replay_latest=False)
        service.start()
        try:
            bus.publish(LOCALIZATION_POSE, pose(0.9, 0.23, 0.31))
            bus.publish(LIDAR_SCAN, self.scan())
            observation = await asyncio.wait_for(output.get(), timeout=1)
        finally:
            output.close()
            await service.stop()

        self.assertEqual(observation.source, "simulation_known_world_scan_matcher")
        self.assertEqual(service.scans_received, 1)
        self.assertEqual(service.matches_published, 1)
        self.assertGreater(service.last_candidates_evaluated, 0)
        self.assertIsNone(service.last_rejection)

    async def test_rejects_missing_and_stale_pose_without_matching(self) -> None:
        bus = TopicBus()
        service = KnownWorldScanMatcherService(
            bus, self.matcher, max_pose_age_seconds=0.005
        )
        service.start()
        try:
            bus.publish(LIDAR_SCAN, self.scan())
            await asyncio.sleep(0)
            bus.publish(
                LOCALIZATION_POSE,
                pose(0.8, 0.3, 0.25, timestamp_ns=900_000_000),
            )
            bus.publish(LIDAR_SCAN, self.scan())
            await asyncio.sleep(0.01)
        finally:
            await service.stop()

        self.assertEqual(service.rejected_missing_pose, 1)
        self.assertEqual(service.rejected_pose_timing, 1)
        self.assertEqual(service.matches_published, 0)

    async def test_uses_historical_pose_not_newer_than_scan(self) -> None:
        bus = TopicBus()
        service = KnownWorldScanMatcherService(
            bus, self.matcher, max_pose_age_seconds=0.2
        )
        output = bus.subscribe(POSE_OBSERVATION, replay_latest=False)
        service.start()
        try:
            bus.publish(
                LOCALIZATION_POSE,
                pose(0.9, 0.23, 0.31, timestamp_ns=990_000_000),
            )
            await asyncio.sleep(0)
            bus.publish(
                LOCALIZATION_POSE,
                pose(0.9, 0.23, 0.31, timestamp_ns=1_010_000_000),
            )
            await asyncio.sleep(0)
            bus.publish(LIDAR_SCAN, self.scan())

            observation = await asyncio.wait_for(output.get(), timeout=1)
        finally:
            output.close()
            await service.stop()

        self.assertEqual(observation.header.timestamp_monotonic_ns, 1_000_000_000)
        self.assertEqual(service.matches_published, 1)
        self.assertEqual(service.rejected_pose_timing, 0)


if __name__ == "__main__":
    unittest.main()
