import asyncio
import math
import unittest
from typing import Iterator, List, Optional

from app.services.autonomy import (
    EncoderPublisherService,
    IMUPublisherService,
    LaserScanConverter,
    LidarPublisherService,
    LocalizationSensorService,
    TopicBus,
    UnavailableEncoderPublisher,
)
from app.services.autonomy.topics import ENCODER_STATE, IMU_DATA, LIDAR_SCAN
from robot_hat import (
    EncoderABC,
    EncoderHealth,
    EncoderSample,
    IMUABC,
    IMUSample,
    Lidar2DABC,
    LidarDeviceInfo,
    LidarHealth,
    LidarHealthStatus,
    LidarMeasurement,
    LidarScan,
)


class FakeIMU(IMUABC):
    def __init__(self) -> None:
        self.initialized = False
        self.close_calls = 0
        self.reads = 0

    def initialize(self) -> None:
        self.initialized = True

    def read_sample(self) -> IMUSample:
        self.reads += 1
        return IMUSample(
            acceleration_mps2=(1.0, 2.0, 3.0),
            angular_velocity_radps=(0.1, 0.2, 0.3),
            timestamp_monotonic_ns=self.reads * 100,
        )

    def close(self) -> None:
        self.close_calls += 1


class FakeEncoder(EncoderABC):
    def __init__(self, samples: List[EncoderSample]) -> None:
        self.samples = iter(samples)
        self.initialized = False
        self.closed = False

    def initialize(self) -> None:
        self.initialized = True

    def read_sample(self) -> EncoderSample:
        return next(self.samples)

    def read_health(self) -> EncoderHealth:
        return EncoderHealth(available=self.initialized and not self.closed)

    def reset(self, ticks: int = 0) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class FakeLidar(Lidar2DABC):
    def __init__(self, scans: List[LidarScan]) -> None:
        self.scans = scans
        self._connected = False
        self._scanning = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_scanning(self) -> bool:
        return self._scanning

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def get_device_info(self) -> LidarDeviceInfo:
        return LidarDeviceInfo("test", "fake", "1", "1", "1")

    def get_health(self) -> LidarHealth:
        return LidarHealth(LidarHealthStatus.OK)

    def reset(self) -> None:
        return None

    def start_scan(self) -> None:
        self._scanning = True

    def stop_scan(self) -> None:
        self._scanning = False

    def iter_measurements(self) -> Iterator[LidarMeasurement]:
        return iter(())

    def iter_scans(
        self,
        *,
        min_measurements: int = 1,
        max_scans: Optional[int] = None,
    ) -> Iterator[LidarScan]:
        return iter(self.scans)


def measurement(
    angle_deg: float,
    distance_m: float,
    *,
    quality: int = 10,
    timestamp: float = 1.0,
) -> LidarMeasurement:
    return LidarMeasurement(
        angle_deg=angle_deg,
        distance_m=distance_m,
        quality=quality,
        start_of_scan=angle_deg == 0,
        timestamp=timestamp,
    )


class TestLaserScanConverter(unittest.TestCase):
    def test_bins_irregular_points_and_keeps_nearest_range(self) -> None:
        converter = LaserScanConverter(
            frame_id="laser",
            range_min_m=0.1,
            range_max_m=10.0,
            angular_resolution_deg=45,
            monotonic_ns=lambda: 2_000_000_000,
        )
        scan = LidarScan(
            measurements=(
                measurement(1, 3.0, quality=5),
                measurement(359, 2.0, quality=9),
                measurement(90, 0.05),
                measurement(180, 4.0, quality=7),
            ),
            started_at=1.0,
            ended_at=1.5,
        )

        message = converter.convert(scan, sequence=3)

        self.assertEqual(message.header.sequence, 3)
        self.assertEqual(message.header.source_timestamp_ns, 1_500_000_000)
        self.assertEqual(
            message.ranges_m,
            (2.0, math.inf, math.inf, math.inf, 4.0, math.inf, math.inf, math.inf),
        )
        self.assertEqual(
            message.intensities,
            (9.0, 0.0, 0.0, 0.0, 7.0, 0.0, 0.0, 0.0),
        )
        self.assertAlmostEqual(message.angle_increment_rad, math.pi / 4)


class TestSensorPublishers(unittest.IsolatedAsyncioTestCase):
    async def test_imu_publisher_maps_si_sample_to_topic(self) -> None:
        bus = TopicBus()
        output = bus.subscribe(IMU_DATA, replay_latest=False)
        imu = FakeIMU()
        service = IMUPublisherService(
            bus,
            lambda: imu,
            frame_id="imu",
            sample_frequency_hz=100,
            monotonic_ns=lambda: 1_000,
        )

        await service.start()
        message = await asyncio.wait_for(output.get(), timeout=1)
        await service.stop()

        self.assertTrue(imu.initialized)
        self.assertEqual(imu.close_calls, 1)
        self.assertEqual(message.angular_velocity_z_radps, 0.3)
        self.assertEqual(message.acceleration_z_mps2, 3.0)
        self.assertEqual(message.header.source_timestamp_ns, 100)
        self.assertEqual(service.status.published_messages, 1)

    async def test_encoder_publisher_derives_delta_without_mutating_adapter(
        self,
    ) -> None:
        bus = TopicBus()
        output = bus.subscribe(ENCODER_STATE, max_queue_size=2, replay_latest=False)
        encoder = FakeEncoder(
            [
                EncoderSample(ticks=10, timestamp_monotonic_ns=100),
                EncoderSample(ticks=14, timestamp_monotonic_ns=200),
            ]
        )
        service = EncoderPublisherService(
            bus,
            lambda: encoder,
            frame_id="encoder",
            sample_frequency_hz=1000,
            monotonic_ns=lambda: 1_000,
        )

        await service.start()
        first = await asyncio.wait_for(output.get(), timeout=1)
        second = await asyncio.wait_for(output.get(), timeout=1)
        await service.stop()

        self.assertEqual((first.ticks, first.delta_ticks), (10, 0))
        self.assertEqual((second.ticks, second.delta_ticks), (14, 4))
        self.assertTrue(encoder.closed)

    async def test_lidar_publisher_connects_validates_and_publishes(self) -> None:
        bus = TopicBus()
        output = bus.subscribe(LIDAR_SCAN, replay_latest=False)
        scan = LidarScan(
            measurements=(measurement(0, 1.0), measurement(90, 2.0)),
            started_at=1.0,
            ended_at=1.1,
        )
        lidar = FakeLidar([scan])
        service = LidarPublisherService(
            bus,
            lambda: lidar,
            LaserScanConverter(
                frame_id="laser",
                range_min_m=0.1,
                range_max_m=10,
                angular_resolution_deg=45,
            ),
            min_measurements_per_scan=1,
        )

        await service.start()
        message = await asyncio.wait_for(output.get(), timeout=1)
        await service.stop()

        self.assertEqual(message.ranges_m[0], 1.0)
        self.assertEqual(message.ranges_m[2], 2.0)
        self.assertFalse(lidar.is_connected)
        self.assertFalse(lidar.is_scanning)

    async def test_suite_isolates_unavailable_encoder_and_reports_status(self) -> None:
        suite = LocalizationSensorService(
            {
                "encoder": UnavailableEncoderPublisher(
                    "concrete encoder is not installed"
                )
            },
            enabled_sensors=("encoder",),
        )

        await suite.start()
        statuses = {status.sensor: status for status in suite.status.sensors}

        self.assertFalse(statuses["lidar"].enabled)
        self.assertTrue(statuses["encoder"].enabled)
        self.assertIn("not installed", statuses["encoder"].error or "")


if __name__ == "__main__":
    unittest.main()
