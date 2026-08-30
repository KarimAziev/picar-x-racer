"""Lifecycle-managed publishers from robot-hat devices to native topics."""

import asyncio
import math
import time
from dataclasses import dataclass
from typing import (
    Callable,
    Dict,
    Iterator,
    Literal,
    Mapping,
    Optional,
    Protocol,
    Sequence,
)

from app.core.px_logger import Logger
from app.schemas.autonomy import (
    EncoderReading,
    EncoderState,
    ImuData,
    LaserScan,
    LocalizationSensorStatus,
    MessageHeader,
    SensorName,
    SensorPublisherStatus,
)
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import ENCODER_STATE, IMU_DATA, LIDAR_SCAN
from robot_hat import EncoderABC, IMUABC, Lidar2DABC, LidarScan


_log = Logger(__name__)


@dataclass
class _PublisherMetrics:
    published_messages: int = 0
    last_timestamp_monotonic_ns: Optional[int] = None
    error: Optional[str] = None


class SensorPublisher(Protocol):
    sensor_name: SensorName

    @property
    def running(self) -> bool: ...

    @property
    def status(self) -> SensorPublisherStatus: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...


class LaserScanConverter:
    """Bin irregular polar samples into a ROS-compatible uniform scan."""

    def __init__(
        self,
        *,
        frame_id: str,
        range_min_m: float,
        range_max_m: float,
        angular_resolution_deg: float,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if range_min_m < 0 or range_max_m <= range_min_m:
            raise ValueError("invalid lidar range limits")
        if not 0 < angular_resolution_deg <= 45:
            raise ValueError("angular_resolution_deg must be in (0, 45]")
        self.frame_id = frame_id
        self.range_min_m = range_min_m
        self.range_max_m = range_max_m
        self.bin_count = max(1, round(360.0 / angular_resolution_deg))
        self.angle_increment_rad = 2 * math.pi / self.bin_count
        self._monotonic_ns = monotonic_ns

    def convert(self, scan: LidarScan, *, sequence: int) -> LaserScan:
        ranges = [math.inf] * self.bin_count
        intensities = [0.0] * self.bin_count
        for measurement in scan.measurements:
            distance = measurement.distance_m
            if not self.range_min_m <= distance <= self.range_max_m:
                continue
            angle_rad = math.radians(measurement.angle_deg)
            index = int(angle_rad / self.angle_increment_rad + 0.5) % self.bin_count
            if distance < ranges[index]:
                ranges[index] = distance
                intensities[index] = float(measurement.quality)

        return LaserScan(
            header=MessageHeader(
                sequence=sequence,
                frame_id=self.frame_id,
                timestamp_monotonic_ns=self._monotonic_ns(),
                source_timestamp_ns=max(0, int(scan.ended_at * 1_000_000_000)),
            ),
            angle_min_rad=0.0,
            angle_max_rad=(self.bin_count - 1) * self.angle_increment_rad,
            angle_increment_rad=self.angle_increment_rad,
            range_min_m=self.range_min_m,
            range_max_m=self.range_max_m,
            ranges_m=tuple(ranges),
            intensities=tuple(intensities),
        )


def _next_scan(iterator: Iterator[LidarScan]) -> Optional[LidarScan]:
    try:
        return next(iterator)
    except StopIteration:
        return None


class LidarPublisherService:
    sensor_name: SensorName = "lidar"

    def __init__(
        self,
        bus: TopicBus,
        lidar_factory: Callable[[], Lidar2DABC],
        converter: LaserScanConverter,
        *,
        min_measurements_per_scan: int,
    ) -> None:
        self._bus = bus
        self._lidar_factory = lidar_factory
        self._converter = converter
        self._min_measurements_per_scan = min_measurements_per_scan
        self._lidar: Optional[Lidar2DABC] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_requested = False
        self._metrics = _PublisherMetrics()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def status(self) -> SensorPublisherStatus:
        return SensorPublisherStatus(
            sensor=self.sensor_name,
            enabled=True,
            running=self.running,
            published_messages=self._metrics.published_messages,
            last_timestamp_monotonic_ns=(self._metrics.last_timestamp_monotonic_ns),
            error=self._metrics.error,
        )

    async def start(self) -> None:
        if self.running:
            return
        self._metrics.error = None
        self._stop_requested = False
        try:
            lidar = await asyncio.to_thread(self._lidar_factory)
            self._lidar = lidar
            await asyncio.to_thread(lidar.connect)
            health = await asyncio.to_thread(lidar.get_health)
            if not health.is_usable:
                raise RuntimeError(
                    f"lidar health is {health.status.value}: {health.error_code}"
                )
            await asyncio.to_thread(lidar.start_scan)
            iterator = lidar.iter_scans(
                min_measurements=self._min_measurements_per_scan
            )
            self._task = asyncio.create_task(
                self._publish_loop(iterator),
                name="lidar-scan-publisher",
            )
        except Exception as error:
            self._metrics.error = str(error)
            await self._close_lidar()
            raise

    async def stop(self) -> None:
        self._stop_requested = True
        task = self._task
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=2.0)
            except asyncio.TimeoutError:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            self._task = None
        await self._close_lidar()

    async def _publish_loop(self, iterator: Iterator[LidarScan]) -> None:
        try:
            while not self._stop_requested:
                scan = await asyncio.to_thread(_next_scan, iterator)
                if scan is None:
                    return
                sequence = self._metrics.published_messages + 1
                message = self._converter.convert(scan, sequence=sequence)
                self._bus.publish(LIDAR_SCAN, message)
                self._metrics.published_messages = sequence
                self._metrics.last_timestamp_monotonic_ns = (
                    message.header.timestamp_monotonic_ns
                )
                self._metrics.error = None
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._metrics.error = str(error)
            _log.error("LiDAR publisher stopped after an error: %s", error)

    async def _close_lidar(self) -> None:
        lidar = self._lidar
        self._lidar = None
        if lidar is None:
            return
        try:
            if lidar.is_connected and lidar.is_scanning:
                await asyncio.to_thread(lidar.stop_scan)
        finally:
            if lidar.is_connected:
                await asyncio.to_thread(lidar.disconnect)


class IMUPublisherService:
    sensor_name: SensorName = "imu"

    def __init__(
        self,
        bus: TopicBus,
        imu_factory: Callable[[], IMUABC],
        *,
        frame_id: str,
        sample_frequency_hz: float,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self._bus = bus
        self._imu_factory = imu_factory
        self._frame_id = frame_id
        self._period_s = 1.0 / sample_frequency_hz
        self._monotonic_ns = monotonic_ns
        self._imu: Optional[IMUABC] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_requested = False
        self._metrics = _PublisherMetrics()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def status(self) -> SensorPublisherStatus:
        return SensorPublisherStatus(
            sensor=self.sensor_name,
            enabled=True,
            running=self.running,
            published_messages=self._metrics.published_messages,
            last_timestamp_monotonic_ns=(self._metrics.last_timestamp_monotonic_ns),
            error=self._metrics.error,
        )

    async def start(self) -> None:
        if self.running:
            return
        self._metrics.error = None
        self._stop_requested = False
        try:
            imu = await asyncio.to_thread(self._imu_factory)
            self._imu = imu
            await asyncio.to_thread(imu.initialize)
            self._task = asyncio.create_task(
                self._publish_loop(),
                name="imu-data-publisher",
            )
        except Exception as error:
            self._metrics.error = str(error)
            await self._close_imu()
            raise

    async def stop(self) -> None:
        self._stop_requested = True
        task = self._task
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=max(1.0, self._period_s * 2))
            except asyncio.TimeoutError:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            self._task = None
        await self._close_imu()

    async def _publish_loop(self) -> None:
        imu = self._imu
        if imu is None:
            return
        loop = asyncio.get_running_loop()
        next_read = loop.time()
        try:
            while not self._stop_requested:
                sample = await asyncio.to_thread(imu.read_sample)
                sequence = self._metrics.published_messages + 1
                message = ImuData(
                    header=MessageHeader(
                        sequence=sequence,
                        frame_id=self._frame_id,
                        timestamp_monotonic_ns=self._monotonic_ns(),
                        source_timestamp_ns=sample.timestamp_monotonic_ns,
                    ),
                    angular_velocity_z_radps=sample.angular_velocity_radps[2],
                    acceleration_x_mps2=sample.acceleration_mps2[0],
                    acceleration_y_mps2=sample.acceleration_mps2[1],
                    acceleration_z_mps2=sample.acceleration_mps2[2],
                )
                self._bus.publish(IMU_DATA, message)
                self._metrics.published_messages = sequence
                self._metrics.last_timestamp_monotonic_ns = (
                    message.header.timestamp_monotonic_ns
                )
                self._metrics.error = None
                next_read += self._period_s
                await asyncio.sleep(max(0.0, next_read - loop.time()))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._metrics.error = str(error)
            _log.error("IMU publisher stopped after an error: %s", error)

    async def _close_imu(self) -> None:
        imu = self._imu
        self._imu = None
        if imu is not None:
            await asyncio.to_thread(imu.close)


class EncoderPublisherService:
    """Publish one synchronized rear-axle state from one or two encoders."""

    sensor_name: SensorName = "encoder"

    def __init__(
        self,
        bus: TopicBus,
        encoder_factories: Mapping[Literal["left", "right"], Callable[[], EncoderABC]],
        *,
        frame_id: str,
        sample_frequency_hz: float,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if not encoder_factories:
            raise ValueError("at least one encoder factory is required")
        self._bus = bus
        self._encoder_factories = dict(encoder_factories)
        self._frame_id = frame_id
        self._period_s = 1.0 / sample_frequency_hz
        self._monotonic_ns = monotonic_ns
        self._encoders: Dict[Literal["left", "right"], EncoderABC] = {}
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_requested = False
        self._previous_ticks: Dict[Literal["left", "right"], int] = {}
        self._previous_source_timestamps_ns: Dict[Literal["left", "right"], int] = {}
        self._metrics = _PublisherMetrics()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def status(self) -> SensorPublisherStatus:
        return SensorPublisherStatus(
            sensor=self.sensor_name,
            enabled=True,
            running=self.running,
            published_messages=self._metrics.published_messages,
            last_timestamp_monotonic_ns=(self._metrics.last_timestamp_monotonic_ns),
            error=self._metrics.error,
        )

    async def start(self) -> None:
        if self.running:
            return
        self._metrics.error = None
        self._stop_requested = False
        self._previous_ticks.clear()
        self._previous_source_timestamps_ns.clear()
        try:
            for side in ("left", "right"):
                factory = self._encoder_factories.get(side)
                if factory is None:
                    continue
                encoder = await asyncio.to_thread(factory)
                self._encoders[side] = encoder
                await asyncio.to_thread(encoder.initialize)
                health = await asyncio.to_thread(encoder.read_health)
                if not health.available:
                    raise RuntimeError(
                        f"{side} encoder is unavailable after initialization"
                    )
            self._task = asyncio.create_task(
                self._publish_loop(),
                name="rear-encoder-state-publisher",
            )
        except Exception as error:
            self._metrics.error = str(error)
            await self._close_encoder()
            raise

    async def stop(self) -> None:
        self._stop_requested = True
        task = self._task
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=max(1.0, self._period_s * 2))
            except asyncio.TimeoutError:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            self._task = None
        await self._close_encoder()

    async def _publish_loop(self) -> None:
        if not self._encoders:
            return
        loop = asyncio.get_running_loop()
        next_read = loop.time()
        try:
            while not self._stop_requested:
                readings: Dict[Literal["left", "right"], EncoderReading] = {}
                source_timestamps_ns = []
                for side in ("left", "right"):
                    encoder = self._encoders.get(side)
                    if encoder is None:
                        continue
                    sample = await asyncio.to_thread(encoder.read_sample)
                    previous_timestamp_ns = self._previous_source_timestamps_ns.get(
                        side
                    )
                    if (
                        previous_timestamp_ns is not None
                        and sample.timestamp_monotonic_ns <= previous_timestamp_ns
                    ):
                        raise ValueError(
                            f"{side} encoder timestamps must increase monotonically"
                        )
                    previous_ticks = self._previous_ticks.get(side)
                    readings[side] = EncoderReading(
                        ticks=sample.ticks,
                        delta_ticks=(
                            0
                            if previous_ticks is None
                            else sample.ticks - previous_ticks
                        ),
                    )
                    self._previous_ticks[side] = sample.ticks
                    self._previous_source_timestamps_ns[side] = (
                        sample.timestamp_monotonic_ns
                    )
                    source_timestamps_ns.append(sample.timestamp_monotonic_ns)
                sequence = self._metrics.published_messages + 1
                message = EncoderState(
                    header=MessageHeader(
                        sequence=sequence,
                        frame_id=self._frame_id,
                        timestamp_monotonic_ns=self._monotonic_ns(),
                        source_timestamp_ns=max(source_timestamps_ns),
                    ),
                    left=readings.get("left"),
                    right=readings.get("right"),
                )
                self._bus.publish(ENCODER_STATE, message)
                self._metrics.published_messages = sequence
                self._metrics.last_timestamp_monotonic_ns = (
                    message.header.timestamp_monotonic_ns
                )
                self._metrics.error = None
                next_read += self._period_s
                await asyncio.sleep(max(0.0, next_read - loop.time()))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._metrics.error = str(error)
            _log.error("Encoder publisher stopped after an error: %s", error)

    async def _close_encoder(self) -> None:
        encoders = tuple(self._encoders.values())
        self._encoders.clear()
        results = await asyncio.gather(
            *(asyncio.to_thread(encoder.close) for encoder in encoders),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, BaseException):
                raise result


class UnavailableEncoderPublisher:
    """Diagnostic placeholder until a concrete robot-hat encoder is configured."""

    sensor_name: SensorName = "encoder"

    def __init__(self, reason: str) -> None:
        self._reason = reason

    @property
    def running(self) -> bool:
        return False

    @property
    def status(self) -> SensorPublisherStatus:
        return SensorPublisherStatus(
            sensor=self.sensor_name,
            enabled=True,
            running=False,
            error=self._reason,
        )

    async def start(self) -> None:
        raise RuntimeError(self._reason)

    async def stop(self) -> None:
        return None


class LocalizationSensorService:
    """Start, stop, and report configured sensor publishers independently."""

    _SENSOR_ORDER: Sequence[SensorName] = ("lidar", "imu", "encoder")

    def __init__(
        self,
        publishers: Mapping[SensorName, SensorPublisher],
        *,
        enabled_sensors: Sequence[SensorName],
    ) -> None:
        self._publishers: Dict[SensorName, SensorPublisher] = dict(publishers)
        self._enabled_sensors = set(enabled_sensors)

    @property
    def status(self) -> LocalizationSensorStatus:
        statuses = []
        for sensor_name in self._SENSOR_ORDER:
            publisher = self._publishers.get(sensor_name)
            if publisher is not None:
                statuses.append(publisher.status)
            else:
                statuses.append(
                    SensorPublisherStatus(
                        sensor=sensor_name,
                        enabled=sensor_name in self._enabled_sensors,
                        running=False,
                    )
                )
        return LocalizationSensorStatus(sensors=tuple(statuses))

    async def start(self) -> None:
        for sensor_name in self._SENSOR_ORDER:
            publisher = self._publishers.get(sensor_name)
            if publisher is None:
                continue
            try:
                await publisher.start()
            except Exception as error:
                _log.error("Failed to start %s publisher: %s", sensor_name, error)

    async def stop(self) -> None:
        for sensor_name in reversed(self._SENSOR_ORDER):
            publisher = self._publishers.get(sensor_name)
            if publisher is None:
                continue
            try:
                await publisher.stop()
            except Exception as error:
                _log.error("Failed to stop %s publisher: %s", sensor_name, error)


__all__ = [
    "EncoderPublisherService",
    "IMUPublisherService",
    "LaserScanConverter",
    "LidarPublisherService",
    "LocalizationSensorService",
    "UnavailableEncoderPublisher",
]
