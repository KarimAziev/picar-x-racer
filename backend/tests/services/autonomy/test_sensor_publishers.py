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
    StaticRotation3D,
    TopicBus,
    TopicSensorMonitor,
    UnavailableEncoderPublisher,
)
from app.schemas.autonomy import EncoderReading, EncoderState, MessageHeader
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
        self.samples = list(samples)
        self.read_index = 0
        self.initialized = False
        self.closed = False

    def initialize(self) -> None:
        self.initialized = True

    def read_sample(self) -> EncoderSample:
        if self.read_index < len(self.samples):
            sample = self.samples[self.read_index]
            self.read_index += 1
            return sample
        last = self.samples[-1]
        self.read_index += 1
        return EncoderSample(
            ticks=last.ticks,
            timestamp_monotonic_ns=(
                last.timestamp_monotonic_ns
                + 100 * (self.read_index - len(self.samples))
            ),
        )

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


class TestStaticRotation3D(unittest.TestCase):
    def test_identity_preserves_vector(self) -> None:
        self.assertEqual(StaticRotation3D().rotate((1.0, 2.0, 3.0)), (1.0, 2.0, 3.0))

    def test_yaw_rotates_sensor_x_onto_base_y(self) -> None:
        rotated = StaticRotation3D(yaw_rad=math.pi / 2).rotate((1.0, 0.0, 0.0))

        self.assertAlmostEqual(rotated[0], 0.0)
        self.assertAlmostEqual(rotated[1], 1.0)
        self.assertAlmostEqual(rotated[2], 0.0)

    def test_roll_rotates_sensor_y_onto_base_z(self) -> None:
        rotated = StaticRotation3D(roll_rad=math.pi / 2).rotate((0.0, 1.0, 0.0))

        self.assertAlmostEqual(rotated[0], 0.0)
        self.assertAlmostEqual(rotated[1], 0.0)
        self.assertAlmostEqual(rotated[2], 1.0)

    def test_pitch_rotates_sensor_x_onto_negative_base_z(self) -> None:
        rotated = StaticRotation3D(pitch_rad=math.pi / 2).rotate((1.0, 0.0, 0.0))

        self.assertAlmostEqual(rotated[0], 0.0)
        self.assertAlmostEqual(rotated[1], 0.0)
        self.assertAlmostEqual(rotated[2], -1.0)

    def test_rejects_invalid_rotation_or_vector(self) -> None:
        with self.assertRaisesRegex(ValueError, "rotation angles must be finite"):
            StaticRotation3D(yaw_rad=math.inf)
        with self.assertRaisesRegex(ValueError, "three-dimensional"):
            StaticRotation3D().rotate((1.0, 2.0))
        with self.assertRaisesRegex(ValueError, "components must be finite"):
            StaticRotation3D().rotate((1.0, math.nan, 3.0))


class TestSensorPublishers(unittest.IsolatedAsyncioTestCase):
    async def test_topic_monitor_reports_externally_published_simulated_frames(
        self,
    ) -> None:
        bus = TopicBus()
        monitor = TopicSensorMonitor("encoder", bus, ENCODER_STATE)
        await monitor.start()

        bus.publish(
            ENCODER_STATE,
            EncoderState(
                header=MessageHeader(
                    sequence=1,
                    frame_id="rear_axle",
                    timestamp_monotonic_ns=123,
                ),
                left=EncoderReading(ticks=4, delta_ticks=4),
            ),
        )
        await asyncio.sleep(0)

        self.assertTrue(monitor.status.running)
        self.assertEqual(monitor.status.published_messages, 1)
        self.assertEqual(monitor.status.last_timestamp_monotonic_ns, 123)

        await monitor.stop()

        self.assertFalse(monitor.status.running)

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
        self.assertEqual(message.header.frame_id, "base_link")
        self.assertEqual(message.source_frame_id, "imu")
        self.assertEqual(message.angular_velocity_z_radps, 0.3)
        self.assertEqual(message.acceleration_z_mps2, 3.0)
        self.assertEqual(message.header.source_timestamp_ns, 100)
        self.assertEqual(service.status.published_messages, 1)

    async def test_imu_publisher_rotates_sensor_vectors_into_base_link(self) -> None:
        bus = TopicBus()
        output = bus.subscribe(IMU_DATA, replay_latest=False)
        service = IMUPublisherService(
            bus,
            FakeIMU,
            frame_id="sense_hat_imu",
            sample_frequency_hz=100,
            sensor_to_base_rotation=StaticRotation3D(roll_rad=math.pi / 2),
        )

        await service.start()
        message = await asyncio.wait_for(output.get(), timeout=1)
        await service.stop()

        self.assertEqual(message.header.frame_id, "base_link")
        self.assertEqual(message.source_frame_id, "sense_hat_imu")
        self.assertAlmostEqual(message.acceleration_x_mps2, 1.0)
        self.assertAlmostEqual(message.acceleration_y_mps2, -3.0)
        self.assertAlmostEqual(message.acceleration_z_mps2, 2.0)
        self.assertAlmostEqual(message.angular_velocity_z_radps, 0.2)

    async def test_encoder_publisher_derives_delta_without_mutating_adapter(
        self,
    ) -> None:
        bus = TopicBus()
        output = bus.subscribe(ENCODER_STATE, max_queue_size=2, replay_latest=False)
        left_encoder = FakeEncoder(
            [
                EncoderSample(ticks=10, timestamp_monotonic_ns=100),
                EncoderSample(ticks=14, timestamp_monotonic_ns=200),
            ]
        )
        right_encoder = FakeEncoder(
            [
                EncoderSample(ticks=20, timestamp_monotonic_ns=110),
                EncoderSample(ticks=26, timestamp_monotonic_ns=210),
            ]
        )
        service = EncoderPublisherService(
            bus,
            {"left": lambda: left_encoder, "right": lambda: right_encoder},
            frame_id="encoder",
            sample_frequency_hz=1000,
            monotonic_ns=lambda: 1_000,
        )

        await service.start()
        first = await asyncio.wait_for(output.get(), timeout=1)
        second = await asyncio.wait_for(output.get(), timeout=1)
        await service.stop()

        self.assertIsNotNone(first.left)
        self.assertIsNotNone(first.right)
        self.assertIsNotNone(second.left)
        self.assertIsNotNone(second.right)
        assert first.left is not None
        assert first.right is not None
        assert second.left is not None
        assert second.right is not None
        self.assertEqual((first.left.ticks, first.left.delta_ticks), (10, 0))
        self.assertEqual((first.right.ticks, first.right.delta_ticks), (20, 0))
        self.assertEqual((second.left.ticks, second.left.delta_ticks), (14, 4))
        self.assertEqual((second.right.ticks, second.right.delta_ticks), (26, 6))
        self.assertEqual(second.mean_delta_ticks, 5)
        self.assertTrue(left_encoder.closed)
        self.assertTrue(right_encoder.closed)

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

    async def test_suite_reconfigures_running_publishers_in_place(self) -> None:
        first = FakeIMU()
        second = FakeIMU()
        suite = LocalizationSensorService(
            {
                "imu": IMUPublisherService(
                    TopicBus(),
                    lambda: first,
                    frame_id="imu",
                    sample_frequency_hz=100,
                )
            },
            enabled_sensors=("imu",),
        )

        await suite.start()
        await suite.reconfigure(
            {
                "imu": IMUPublisherService(
                    TopicBus(),
                    lambda: second,
                    frame_id="imu_reconfigured",
                    sample_frequency_hz=100,
                )
            },
            enabled_sensors=("imu",),
        )
        await asyncio.sleep(0)
        await suite.stop()

        self.assertEqual(first.close_calls, 1)
        self.assertTrue(second.initialized)
        self.assertEqual(second.close_calls, 1)


if __name__ == "__main__":
    unittest.main()
