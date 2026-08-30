"""Calibration from absolute linkage position to signed road-wheel steering."""

import asyncio
import math
import time
from dataclasses import dataclass
from threading import Lock
from typing import Callable, Optional, Tuple

from robot_hat import AngularPositionABC


@dataclass(frozen=True)
class SteeringCalibrationPoint:
    """One measured linkage offset and corresponding signed wheel angle."""

    sensor_offset_deg: float
    wheel_angle_rad: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.sensor_offset_deg):
            raise ValueError("sensor_offset_deg must be finite")
        if not math.isfinite(self.wheel_angle_rad):
            raise ValueError("wheel_angle_rad must be finite")


@dataclass(frozen=True)
class SteeringAngleCalibration:
    """Convert a `[0, 360)` linkage bearing to signed wheel radians.

    With no calibration points, the centered sensor offset is multiplied by
    ``wheel_degrees_per_sensor_degree``. Two or more points enable piecewise
    linear correction for servo/linkage nonlinearity. Point offsets are defined
    after optional direction inversion and must be strictly increasing.
    """

    center_angle_deg: float
    invert_direction: bool = False
    wheel_degrees_per_sensor_degree: float = 1.0
    points: Tuple[SteeringCalibrationPoint, ...] = ()

    def __post_init__(self) -> None:
        if not math.isfinite(self.center_angle_deg):
            raise ValueError("center_angle_deg must be finite")
        if (
            not math.isfinite(self.wheel_degrees_per_sensor_degree)
            or self.wheel_degrees_per_sensor_degree <= 0
        ):
            raise ValueError(
                "wheel_degrees_per_sensor_degree must be finite and positive"
            )
        if len(self.points) == 1:
            raise ValueError(
                "steering calibration requires zero or at least two points"
            )
        previous_offset: float | None = None
        for point in self.points:
            if (
                previous_offset is not None
                and point.sensor_offset_deg <= previous_offset
            ):
                raise ValueError(
                    "steering calibration sensor offsets must increase strictly"
                )
            previous_offset = point.sensor_offset_deg

    def to_wheel_angle_rad(self, absolute_angle_deg: float) -> float:
        """Return signed physical steering, rejecting extrapolation ambiguity."""

        if not math.isfinite(absolute_angle_deg):
            raise ValueError("absolute_angle_deg must be finite")
        offset_deg = (
            absolute_angle_deg - self.center_angle_deg + 180.0
        ) % 360.0 - 180.0
        if self.invert_direction:
            offset_deg = -offset_deg
        if not self.points:
            return math.radians(offset_deg * self.wheel_degrees_per_sensor_degree)
        return self._interpolate(offset_deg)

    def _interpolate(self, sensor_offset_deg: float) -> float:
        first = self.points[0]
        last = self.points[-1]
        if not first.sensor_offset_deg <= sensor_offset_deg <= last.sensor_offset_deg:
            raise ValueError(
                "measured steering position is outside the calibrated linkage range"
            )
        for left, right in zip(self.points, self.points[1:]):
            if sensor_offset_deg <= right.sensor_offset_deg:
                span = right.sensor_offset_deg - left.sensor_offset_deg
                fraction = (sensor_offset_deg - left.sensor_offset_deg) / span
                return left.wheel_angle_rad + fraction * (
                    right.wheel_angle_rad - left.wheel_angle_rad
                )
        return last.wheel_angle_rad


@dataclass(frozen=True)
class SteeringFeedbackSample:
    """Latest calibrated physical road-wheel angle."""

    wheel_angle_rad: float
    timestamp_monotonic_ns: int


class SteeringFeedbackService:
    """Acquire absolute linkage position without blocking the motion loop."""

    def __init__(
        self,
        sensor_factory: Callable[[], AngularPositionABC],
        calibration: SteeringAngleCalibration,
        *,
        sample_frequency_hz: float,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if sample_frequency_hz <= 0 or not math.isfinite(sample_frequency_hz):
            raise ValueError("sample_frequency_hz must be finite and positive")
        self._sensor_factory = sensor_factory
        self._calibration = calibration
        self._period_s = 1.0 / sample_frequency_hz
        self._max_sample_age_ns = max(
            int(3.0 * self._period_s * 1_000_000_000),
            50_000_000,
        )
        self._monotonic_ns = monotonic_ns
        self._sensor: Optional[AngularPositionABC] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._latest: Optional[SteeringFeedbackSample] = None
        self._last_error: Optional[Exception] = None
        self._lock = Lock()

    @property
    def latest(self) -> Optional[SteeringFeedbackSample]:
        with self._lock:
            sample = self._latest
            if sample is None:
                return None
            age_ns = self._monotonic_ns() - sample.timestamp_monotonic_ns
            if age_ns < 0 or age_ns > self._max_sample_age_ns:
                return None
            return sample

    @property
    def last_error(self) -> Optional[Exception]:
        return self._last_error

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.running:
            return
        self._last_error = None
        sensor = await asyncio.to_thread(self._sensor_factory)
        self._sensor = sensor
        try:
            await asyncio.to_thread(sensor.initialize)
            health = await asyncio.to_thread(sensor.read_health)
            if not health.available:
                raise RuntimeError(
                    "steering position sensor is unavailable after initialization"
                )
        except Exception:
            await self._close_sensor()
            raise
        self._task = asyncio.create_task(
            self._sample_loop(), name="steering-position-sampler"
        )

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
        if task is not None:
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self._close_sensor()
        with self._lock:
            self._latest = None

    async def reconfigure_from(self, replacement: "SteeringFeedbackService") -> None:
        """Restart acquisition with a newly validated sensor configuration."""

        was_running = self.running
        await self.stop()
        self._sensor_factory = replacement._sensor_factory
        self._calibration = replacement._calibration
        self._period_s = replacement._period_s
        self._max_sample_age_ns = replacement._max_sample_age_ns
        self._last_error = None
        if was_running:
            await self.start()

    async def _sample_loop(self) -> None:
        sensor = self._sensor
        if sensor is None:
            return
        loop = asyncio.get_running_loop()
        next_read = loop.time()
        try:
            while True:
                sample = await asyncio.to_thread(sensor.read_angle)
                calibrated = SteeringFeedbackSample(
                    wheel_angle_rad=self._calibration.to_wheel_angle_rad(
                        sample.angle_degrees
                    ),
                    timestamp_monotonic_ns=sample.timestamp_monotonic_ns,
                )
                with self._lock:
                    previous = self._latest
                    if (
                        previous is not None
                        and calibrated.timestamp_monotonic_ns
                        <= previous.timestamp_monotonic_ns
                    ):
                        raise ValueError(
                            "steering sensor timestamps must increase monotonically"
                        )
                    self._latest = calibrated
                next_read += self._period_s
                await asyncio.sleep(max(0.0, next_read - loop.time()))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._last_error = error
            with self._lock:
                self._latest = None

    async def _close_sensor(self) -> None:
        sensor = self._sensor
        self._sensor = None
        if sensor is not None:
            await asyncio.to_thread(sensor.close)


__all__ = [
    "SteeringAngleCalibration",
    "SteeringCalibrationPoint",
    "SteeringFeedbackSample",
    "SteeringFeedbackService",
]
