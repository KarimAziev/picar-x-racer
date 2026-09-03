import asyncio
import math
import unittest

from app.schemas.autonomy import (
    LaserScan,
    LocalizationPose2D,
    MappingPoseSource,
    MessageHeader,
    Odometry2D,
)
from app.services.autonomy import (
    LocalMappingService,
    LocalOccupancyGrid,
    LocalOccupancyGridConfig,
    StaticTransform2D,
    TopicBus,
)
from app.services.autonomy.topics import (
    LIDAR_SCAN,
    LOCALIZATION_POSE,
    LOCAL_MAP,
    ODOMETRY,
)


def header(sequence: int, timestamp: int = 100) -> MessageHeader:
    return MessageHeader(
        sequence=sequence,
        frame_id="laser",
        timestamp_monotonic_ns=timestamp,
    )


def scan(distance: float, *, timestamp: int = 100) -> LaserScan:
    return LaserScan(
        header=header(1, timestamp),
        angle_min_rad=0,
        angle_max_rad=0,
        angle_increment_rad=1,
        range_min_m=0.1,
        range_max_m=10,
        ranges_m=(distance,),
    )


def odometry(*, timestamp: int = 100, x_m: float = 0, yaw_rad: float = 0) -> Odometry2D:
    return Odometry2D(
        header=MessageHeader(
            sequence=1,
            frame_id="odom",
            timestamp_monotonic_ns=timestamp,
        ),
        x_m=x_m,
        y_m=0,
        yaw_rad=yaw_rad,
        linear_speed_mps=0,
        yaw_rate_radps=0,
    )


def localization(
    *, timestamp: int = 100, x_m: float = 0, yaw_rad: float = 0
) -> LocalizationPose2D:
    return LocalizationPose2D(
        header=MessageHeader(
            sequence=1,
            frame_id="odom",
            timestamp_monotonic_ns=timestamp,
        ),
        x_m=x_m,
        y_m=0,
        yaw_rad=yaw_rad,
        linear_speed_mps=0,
        yaw_rate_radps=0,
        position_variance_m2=0.001,
        yaw_variance_rad2=0.001,
        fusion_mode="corrected",
    )


class TestLocalOccupancyGrid(unittest.TestCase):
    def test_marks_ray_free_and_endpoint_occupied(self) -> None:
        grid = LocalOccupancyGrid(
            LocalOccupancyGridConfig(width_m=4, height_m=4, resolution_m=1)
        )

        self.assertEqual(grid.insert(scan(1), odometry()), 1)
        message = grid.message(header=header(1))

        center = 2 * message.width + 2
        endpoint = 2 * message.width + 3
        self.assertEqual(message.data[center], 0)
        self.assertEqual(message.data[endpoint], 100)
        self.assertEqual(message.data[0], -1)

    def test_applies_sensor_and_robot_rotation(self) -> None:
        grid = LocalOccupancyGrid(
            LocalOccupancyGridConfig(
                width_m=6,
                height_m=6,
                resolution_m=1,
                sensor_transform=StaticTransform2D(yaw_rad=math.pi / 2),
            )
        )

        grid.insert(scan(1), odometry(yaw_rad=math.pi / 2))
        message = grid.message(header=header(1))

        endpoint_left = 3 * message.width + 2
        self.assertEqual(message.data[endpoint_left], 100)


class TestLocalMappingService(unittest.IsolatedAsyncioTestCase):
    async def test_prefers_fused_localization_for_scan_insertion(self) -> None:
        bus = TopicBus()
        maps = bus.subscribe(LOCAL_MAP, replay_latest=False)
        service = LocalMappingService(
            bus,
            LocalOccupancyGrid(
                LocalOccupancyGridConfig(width_m=6, height_m=6, resolution_m=1)
            ),
            max_odometry_age_seconds=0.1,
            prefer_localization=True,
        )
        service.start()
        service.start_session()
        bus.publish(ODOMETRY, odometry(timestamp=100))
        bus.publish(
            LOCALIZATION_POSE,
            localization(timestamp=100, x_m=1),
        )
        await asyncio.sleep(0)
        bus.publish(LIDAR_SCAN, scan(1, timestamp=110))

        message = await asyncio.wait_for(maps.get(), timeout=1)
        status = service.status
        await service.stop()

        localized_endpoint = 3 * message.width + 5
        raw_endpoint = 3 * message.width + 4
        self.assertEqual(message.data[localized_endpoint], 100)
        self.assertNotEqual(message.data[raw_endpoint], 100)
        self.assertEqual(status.preferred_pose_source, MappingPoseSource.LOCALIZATION)
        self.assertEqual(status.active_pose_source, MappingPoseSource.LOCALIZATION)
        self.assertEqual(status.scans_inserted_with_localization, 1)
        self.assertEqual(status.scans_inserted_with_odometry, 0)
        self.assertEqual(status.localization_fallbacks, 0)

    async def test_falls_back_to_fresh_odometry_when_localization_is_absent(
        self,
    ) -> None:
        bus = TopicBus()
        maps = bus.subscribe(LOCAL_MAP, replay_latest=False)
        service = LocalMappingService(
            bus,
            LocalOccupancyGrid(
                LocalOccupancyGridConfig(width_m=4, height_m=4, resolution_m=1)
            ),
            max_odometry_age_seconds=0.1,
            prefer_localization=True,
        )
        service.start()
        service.start_session()
        bus.publish(ODOMETRY, odometry(timestamp=100))
        await asyncio.sleep(0)
        bus.publish(LIDAR_SCAN, scan(1, timestamp=110))

        await asyncio.wait_for(maps.get(), timeout=1)
        status = service.status
        await service.stop()

        self.assertEqual(status.active_pose_source, MappingPoseSource.ODOMETRY)
        self.assertEqual(status.scans_inserted_with_localization, 0)
        self.assertEqual(status.scans_inserted_with_odometry, 1)
        self.assertEqual(status.localization_fallbacks, 1)

    async def test_falls_back_when_localization_is_stale(self) -> None:
        bus = TopicBus()
        maps = bus.subscribe(LOCAL_MAP, replay_latest=False)
        service = LocalMappingService(
            bus,
            LocalOccupancyGrid(
                LocalOccupancyGridConfig(width_m=4, height_m=4, resolution_m=1)
            ),
            max_odometry_age_seconds=0.0000001,
            prefer_localization=True,
        )
        service.start()
        service.start_session()
        bus.publish(ODOMETRY, odometry(timestamp=1_000))
        bus.publish(LOCALIZATION_POSE, localization(timestamp=100))
        await asyncio.sleep(0)
        bus.publish(LIDAR_SCAN, scan(1, timestamp=1_010))

        await asyncio.wait_for(maps.get(), timeout=1)
        status = service.status
        await service.stop()

        self.assertEqual(status.active_pose_source, MappingPoseSource.ODOMETRY)
        self.assertEqual(status.localization_fallbacks, 1)

    async def test_selects_latest_localization_not_newer_than_scan(self) -> None:
        bus = TopicBus()
        maps = bus.subscribe(LOCAL_MAP, replay_latest=False)
        service = LocalMappingService(
            bus,
            LocalOccupancyGrid(
                LocalOccupancyGridConfig(width_m=8, height_m=8, resolution_m=1)
            ),
            max_odometry_age_seconds=0.1,
            prefer_localization=True,
        )
        service.start()
        service.start_session()
        bus.publish(LOCALIZATION_POSE, localization(timestamp=90, x_m=1))
        await asyncio.sleep(0)
        bus.publish(LOCALIZATION_POSE, localization(timestamp=110, x_m=-2))
        await asyncio.sleep(0)
        bus.publish(LIDAR_SCAN, scan(1, timestamp=100))

        message = await asyncio.wait_for(maps.get(), timeout=1)
        await service.stop()

        past_pose_endpoint = 4 * message.width + 6
        future_pose_endpoint = 4 * message.width + 3
        self.assertEqual(message.data[past_pose_endpoint], 100)
        self.assertNotEqual(message.data[future_pose_endpoint], 100)

    async def test_publishes_map_from_fresh_odometry_and_scan(self) -> None:
        bus = TopicBus()
        maps = bus.subscribe(LOCAL_MAP, replay_latest=False)
        service = LocalMappingService(
            bus,
            LocalOccupancyGrid(
                LocalOccupancyGridConfig(width_m=4, height_m=4, resolution_m=1)
            ),
            max_odometry_age_seconds=0.1,
        )
        service.start()
        service.start_session()
        bus.publish(ODOMETRY, odometry(timestamp=100))
        await asyncio.sleep(0)
        bus.publish(LIDAR_SCAN, scan(1, timestamp=110))

        message = await asyncio.wait_for(maps.get(), timeout=1)
        await service.stop()

        self.assertEqual(message.header.frame_id, "odom")
        self.assertIn(100, message.data)

    async def test_rejects_scan_with_stale_odometry(self) -> None:
        bus = TopicBus()
        maps = bus.subscribe(LOCAL_MAP, replay_latest=False)
        service = LocalMappingService(
            bus,
            LocalOccupancyGrid(
                LocalOccupancyGridConfig(width_m=4, height_m=4, resolution_m=1)
            ),
            max_odometry_age_seconds=0.00000001,
        )
        service.start()
        service.start_session()
        bus.publish(ODOMETRY, odometry(timestamp=100))
        await asyncio.sleep(0)
        bus.publish(LIDAR_SCAN, scan(1, timestamp=1_000))
        await asyncio.sleep(0.02)
        await service.stop()

        self.assertEqual(maps.pending_messages, 0)
        self.assertEqual(service.status.rejected_stale_odometry, 1)

    async def test_ignores_scans_until_session_is_started(self) -> None:
        bus = TopicBus()
        maps = bus.subscribe(LOCAL_MAP, replay_latest=False)
        service = LocalMappingService(
            bus,
            LocalOccupancyGrid(
                LocalOccupancyGridConfig(width_m=4, height_m=4, resolution_m=1)
            ),
            max_odometry_age_seconds=0.1,
        )
        service.start()
        bus.publish(ODOMETRY, odometry(timestamp=100))
        await asyncio.sleep(0)
        bus.publish(LIDAR_SCAN, scan(1, timestamp=110))
        await asyncio.sleep(0.02)
        await service.stop()

        self.assertEqual(maps.pending_messages, 0)
        self.assertEqual(service.status.state.value, "idle")
        self.assertEqual(service.status.ignored_inactive_scans, 1)

    async def test_pause_clear_and_reset_have_explicit_semantics(self) -> None:
        bus = TopicBus()
        maps = bus.subscribe(LOCAL_MAP, replay_latest=False)
        service = LocalMappingService(
            bus,
            LocalOccupancyGrid(
                LocalOccupancyGridConfig(width_m=4, height_m=4, resolution_m=1)
            ),
            max_odometry_age_seconds=0.1,
        )
        service.start()
        started = service.start_session()
        self.assertEqual(started.session_id, 1)
        bus.publish(ODOMETRY, odometry(timestamp=100))
        await asyncio.sleep(0)
        bus.publish(LIDAR_SCAN, scan(1, timestamp=110))
        await asyncio.wait_for(maps.get(), timeout=1)

        paused = service.pause_session()
        self.assertEqual(paused.state.value, "paused")
        bus.publish(LIDAR_SCAN, scan(1, timestamp=120))
        await asyncio.sleep(0.02)
        self.assertEqual(service.status.ignored_inactive_scans, 1)

        cleared = service.clear_map()
        cleared_map = await asyncio.wait_for(maps.get(), timeout=1)
        self.assertEqual(cleared.state.value, "paused")
        self.assertFalse(cleared.has_map)
        self.assertTrue(all(value == -1 for value in cleared_map.data))

        resumed = service.start_session()
        self.assertEqual(resumed.state.value, "active")
        self.assertEqual(resumed.session_id, 1)
        reset = service.reset_session()
        reset_map = await asyncio.wait_for(maps.get(), timeout=1)
        await service.stop()

        self.assertEqual(reset.state.value, "idle")
        self.assertEqual(reset.scans_received, 0)
        self.assertEqual(reset.session_id, 1)
        self.assertTrue(all(value == -1 for value in reset_map.data))


if __name__ == "__main__":
    unittest.main()
