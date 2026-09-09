import asyncio
import math
import threading
import unittest
from unittest.mock import patch

from app.schemas.autonomy import (
    MappingSessionState,
    MappingSessionStatus,
    MessageHeader,
    OccupancyGrid,
)
from app.schemas.robot.pose_estimation import OccupancyMapScanMatchingConfig
from app.services.autonomy.local_mapping import (
    LocalOccupancyGrid,
    LocalOccupancyGridConfig,
)
from app.services.autonomy.occupancy_scan_matching import (
    OccupancyDistanceField,
    OccupancyMapScanMatcher,
    OccupancyMapScanMatcherService,
)
from app.services.autonomy.scan_matching import KnownWorldScanMatcherConfig
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import (
    LIDAR_SCAN,
    LOCALIZATION_POSE,
    LOCAL_MAP,
    MAPPING_SESSION,
    POSE_OBSERVATION,
)
from tests.services.autonomy.test_scan_matching import ScanMatchingFixture, pose


class ObservedMapFixture(ScanMatchingFixture):
    def setUp(self) -> None:
        super().setUp()
        occupancy = LocalOccupancyGrid(
            LocalOccupancyGridConfig(
                width_m=8,
                height_m=8,
                resolution_m=0.05,
                sensor_transform=self.sensor_transform,
            )
        )
        # Only measured rays and mapping poses enter the reference, not world segments.
        for x, y, yaw in ((0.8, 0.3, 0.25), (0.7, 0.2, 0.1), (0.9, 0.4, 0.4)):
            occupancy.insert(self.scan(x, y, yaw), pose(x, y, yaw))
        self.grid = occupancy.message(
            header=MessageHeader(
                frame_id="odom",
                sequence=12,
                timestamp_monotonic_ns=900_000_000,
            )
        )
        self.settings = OccupancyMapScanMatchingConfig(enabled=True)
        self.config = KnownWorldScanMatcherConfig(
            odom_origin_in_world=(0, 0, 0),
            sensor_transform=self.sensor_transform,
            expected_scan_frame_id="laser",
        )
        self.observed_matcher = OccupancyMapScanMatcher(
            self.grid, self.config, self.settings
        )


class TestObservedMapMatcher(ObservedMapFixture, unittest.TestCase):
    def test_recovers_biased_pose_from_observed_cells(self) -> None:
        result = self.observed_matcher.match(
            self.scan(), pose(0.9, 0.23, 0.31), sequence=5
        )
        self.assertTrue(result.accepted, result)
        observation = result.observation
        assert observation is not None
        self.assertAlmostEqual(observation.x_m, 0.8, delta=0.05)
        self.assertAlmostEqual(observation.y_m, 0.3, delta=0.05)
        self.assertAlmostEqual(observation.yaw_rad, 0.25, delta=0.025)
        self.assertEqual(observation.source, "occupancy_map_scan_matcher")
        self.assertLess(result.mean_error_m or 1, result.prior_mean_error_m or 0)
        self.assertEqual(observation.header.frame_id, "odom")

    def test_unknown_map_and_mismatched_frames_are_rejected(self) -> None:
        unknown = self.grid.model_copy(update={"data": (-1,) * len(self.grid.data)})
        with self.assertRaisesRegex(ValueError, "too few occupied"):
            OccupancyMapScanMatcher(unknown, self.config, self.settings)
        with self.assertRaisesRegex(ValueError, "frames do not match"):
            self.observed_matcher.match(
                self.scan(),
                pose(0.8, 0.3, 0.25).model_copy(
                    update={
                        "header": MessageHeader(
                            frame_id="map", sequence=0, timestamp_monotonic_ns=1
                        )
                    }
                ),
                sequence=1,
            )

    def test_parallel_wall_is_ambiguous(self) -> None:
        grid = OccupancyGrid(
            header=self.grid.header,
            width=100,
            height=100,
            resolution_m=0.05,
            origin_x_m=0,
            origin_y_m=0,
            data=tuple(100 if index // 100 == 90 else 0 for index in range(10000)),
        )
        scan = self.scan().model_copy(
            update={
                "angle_min_rad": math.pi / 4,
                "angle_increment_rad": math.pi / 62,
                "ranges_m": tuple(
                    (4.525 - 2.5) / math.sin(math.pi / 4 + i * math.pi / 62)
                    for i in range(32)
                ),
            }
        )
        matcher = OccupancyMapScanMatcher(
            grid,
            KnownWorldScanMatcherConfig(
                odom_origin_in_world=(0, 0, 0), expected_scan_frame_id="laser"
            ),
            self.settings,
        )
        result = matcher.match(scan, pose(2.5, 2.5, 0), sequence=1)
        self.assertEqual(result.rejection, "ambiguous_alignment")

    def test_search_boundary_is_rejected_even_with_a_good_residual(self) -> None:
        result = self.observed_matcher.match(
            self.scan(), pose(1.0, 0.3, 0.25), sequence=1
        )
        self.assertLess(result.mean_error_m or 1, self.config.max_mean_error_m)
        self.assertEqual(result.rejection, "search_boundary")

    def test_unknown_robot_origin_is_rejected(self) -> None:
        data = list(self.grid.data)
        for index in range(len(data)):
            x = (
                self.grid.origin_x_m
                + (index % self.grid.width + 0.5) * self.grid.resolution_m
            )
            y = (
                self.grid.origin_y_m
                + (index // self.grid.width + 0.5) * self.grid.resolution_m
            )
            if abs(x - 0.8) < 0.3 and abs(y - 0.3) < 0.3:
                data[index] = -1
        matcher = OccupancyMapScanMatcher(
            self.grid.model_copy(update={"data": tuple(data)}),
            self.config,
            self.settings,
        )
        result = matcher.match(self.scan(), pose(0.8, 0.3, 0.25), sequence=1)
        self.assertEqual(result.rejection, "insufficient_overlap")

    def test_distance_field_honors_rotated_origin_and_unknown_cells(self) -> None:
        grid = OccupancyGrid(
            header=self.grid.header,
            width=3,
            height=3,
            resolution_m=1,
            origin_x_m=10,
            origin_y_m=20,
            origin_yaw_rad=math.pi / 2,
            data=(0, 0, 0, 0, 100, 0, -1, 0, 0),
        )
        field = OccupancyDistanceField(
            grid, threshold=65, cap_m=3, min_occupied_cells=1
        )
        self.assertAlmostEqual(field.distance_to_nearest(8.5, 21.5), 0)
        self.assertAlmostEqual(field.distance_to_nearest(8.5, 20.5), 1)
        self.assertFalse(field.known(7.5, 20.5))
        self.assertEqual(field.distance_to_nearest(7.5, 20.5), 3)
        self.assertEqual(field.distance_to_nearest(0, 0), 3)


class TestObservedMapService(ObservedMapFixture, unittest.IsolatedAsyncioTestCase):
    def publish_reference(self, bus: TopicBus, state: MappingSessionState) -> None:
        bus.publish(LOCAL_MAP, self.grid)
        bus.publish(
            MAPPING_SESSION,
            MappingSessionStatus(
                enabled=True,
                state=state,
                has_map=True,
                map_sequence=self.grid.header.sequence,
            ),
        )

    async def test_waits_for_frozen_map_and_rejects_old_scans(self) -> None:
        bus = TopicBus()
        service = OccupancyMapScanMatcherService(bus, self.config, self.settings)
        self.assertFalse(await service._prepare_reference(self.scan()))
        self.publish_reference(bus, MappingSessionState.ACTIVE)
        self.assertFalse(await service._prepare_reference(self.scan()))
        self.publish_reference(bus, MappingSessionState.PAUSED)
        self.assertTrue(await service._prepare_reference(self.scan()))
        self.assertEqual(service.reference_map_sequence, 12)
        old_scan = self.scan().model_copy(update={"header": self.grid.header})
        self.assertFalse(await service._prepare_reference(old_scan))
        self.publish_reference(bus, MappingSessionState.IDLE)
        self.assertTrue(await service._prepare_reference(self.scan()))
        bus.publish(MAPPING_SESSION, MappingSessionStatus.disabled())
        self.assertFalse(await service._prepare_reference(self.scan()))
        self.assertIsNone(service.reference_map_sequence)

    async def test_publishes_correction_only_while_reference_remains_frozen(
        self,
    ) -> None:
        bus = TopicBus()
        self.publish_reference(bus, MappingSessionState.PAUSED)
        service = OccupancyMapScanMatcherService(bus, self.config, self.settings)
        corrections = bus.subscribe(POSE_OBSERVATION)
        service.start()
        try:
            bus.publish(LOCALIZATION_POSE, pose(0.9, 0.23, 0.31))
            await asyncio.sleep(0)
            bus.publish(LIDAR_SCAN, self.scan())
            observation = await asyncio.wait_for(corrections.get(), timeout=5)
            self.assertEqual(observation.source, "occupancy_map_scan_matcher")
            self.assertEqual(service.matches_published, 1)
        finally:
            await service.stop()
            corrections.close()

    async def test_discards_in_flight_match_when_mapping_restarts(self) -> None:
        bus = TopicBus()
        self.publish_reference(bus, MappingSessionState.PAUSED)
        service = OccupancyMapScanMatcherService(bus, self.config, self.settings)
        self.assertTrue(await service._prepare_reference(self.scan()))
        matcher = service.matcher
        assert matcher is not None
        match = matcher.match
        started, release = threading.Event(), threading.Event()

        def delayed_match():
            started.set()
            if not release.wait(timeout=5):
                raise TimeoutError("test did not release matcher")
            return match(self.scan(), pose(0.9, 0.23, 0.31), sequence=0)

        with patch.object(
            matcher, "match", side_effect=lambda *args, **kwargs: delayed_match()
        ):
            service.start()
            try:
                bus.publish(LOCALIZATION_POSE, pose(0.9, 0.23, 0.31))
                await asyncio.sleep(0)
                bus.publish(LIDAR_SCAN, self.scan())
                self.assertTrue(await asyncio.to_thread(started.wait, 5))
                self.publish_reference(bus, MappingSessionState.ACTIVE)
                release.set()
                async with asyncio.timeout(5):
                    while service.rejected_reference == 0:
                        await asyncio.sleep(0.01)
                self.assertEqual(service.matches_published, 0)
                self.assertIsNone(bus.latest(POSE_OBSERVATION))
            finally:
                release.set()
                await service.stop()
