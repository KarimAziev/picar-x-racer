"""Locally smooth wheel/IMU pose fusion with typed correction observations."""

import asyncio
import math
from dataclasses import dataclass
from typing import Optional

from app.schemas.autonomy import (
    ImuData,
    LocalizationPose2D,
    MessageHeader,
    Odometry2D,
    PoseObservation2D,
)
from app.services.autonomy.topic_bus import TopicBus, TopicSubscription
from app.services.autonomy.topics import (
    IMU_DATA,
    LOCALIZATION_POSE,
    ODOMETRY,
    POSE_OBSERVATION,
)


class PoseEstimationInputError(ValueError):
    """Raised when pose-estimator inputs violate ordering or frame contracts."""


@dataclass(frozen=True)
class PoseEstimatorConfig:
    imu_yaw_rate_weight: float = 0.35
    max_imu_age_seconds: float = 0.1
    max_pose_observation_age_seconds: float = 0.25
    initial_position_stddev_m: float = 0.02
    initial_heading_stddev_rad: float = 0.035
    position_process_noise_m_per_meter: float = 0.02
    heading_process_noise_rad_per_second: float = 0.01
    odometry_heading_noise_fraction: float = 0.05
    imu_yaw_rate_stddev_radps: float = 0.03

    def __post_init__(self) -> None:
        values = (
            self.imu_yaw_rate_weight,
            self.max_imu_age_seconds,
            self.max_pose_observation_age_seconds,
            self.initial_position_stddev_m,
            self.initial_heading_stddev_rad,
            self.position_process_noise_m_per_meter,
            self.heading_process_noise_rad_per_second,
            self.odometry_heading_noise_fraction,
            self.imu_yaw_rate_stddev_radps,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("pose-estimator configuration must be finite")
        if not 0 <= self.imu_yaw_rate_weight <= 1:
            raise ValueError("imu_yaw_rate_weight must be between zero and one")
        if self.max_imu_age_seconds <= 0:
            raise ValueError("max_imu_age_seconds must be greater than zero")
        if self.max_pose_observation_age_seconds <= 0:
            raise ValueError(
                "max_pose_observation_age_seconds must be greater than zero"
            )
        for name, value in (
            ("initial_position_stddev_m", self.initial_position_stddev_m),
            ("initial_heading_stddev_rad", self.initial_heading_stddev_rad),
            (
                "position_process_noise_m_per_meter",
                self.position_process_noise_m_per_meter,
            ),
            (
                "heading_process_noise_rad_per_second",
                self.heading_process_noise_rad_per_second,
            ),
            (
                "odometry_heading_noise_fraction",
                self.odometry_heading_noise_fraction,
            ),
            ("imu_yaw_rate_stddev_radps", self.imu_yaw_rate_stddev_radps),
        ):
            if value < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True)
class PoseEstimatorResult:
    pose: LocalizationPose2D
    imu_used: bool
    imu_rejection: Optional[str] = None
    correction_applied: bool = False
    correction_rejection: Optional[str] = None
    position_innovation_m: Optional[float] = None
    heading_innovation_rad: Optional[float] = None


class PoseEstimator:
    """Fuse odometry increments, gyro yaw rate, and bounded pose corrections."""

    def __init__(self, config: PoseEstimatorConfig) -> None:
        self.config = config
        self.reset()

    def reset(self) -> None:
        self._x_m = 0.0
        self._y_m = 0.0
        self._yaw_rad = 0.0
        self._position_variance_m2 = self.config.initial_position_stddev_m**2
        self._yaw_variance_rad2 = self.config.initial_heading_stddev_rad**2
        self._last_odometry_timestamp_ns: Optional[int] = None
        self._last_odometry_sequence: Optional[int] = None
        self._last_odometry_x_m: Optional[float] = None
        self._last_odometry_y_m: Optional[float] = None
        self._last_odometry_yaw_rad: Optional[float] = None
        self._last_observation_timestamp_ns: Optional[int] = None
        self._last_correction_source: Optional[str] = None
        self._output_sequence = 0

    def update(
        self,
        odometry: Odometry2D,
        *,
        imu: Optional[ImuData] = None,
        observation: Optional[PoseObservation2D] = None,
    ) -> PoseEstimatorResult:
        timestamp_ns = odometry.header.timestamp_monotonic_ns
        if (
            self._last_odometry_sequence is not None
            and odometry.header.sequence <= self._last_odometry_sequence
        ):
            raise PoseEstimationInputError(
                "odometry sequence must increase monotonically"
            )
        if (
            self._last_odometry_timestamp_ns is not None
            and timestamp_ns <= self._last_odometry_timestamp_ns
        ):
            raise PoseEstimationInputError(
                "odometry timestamp must increase monotonically"
            )

        previous_timestamp_ns = self._last_odometry_timestamp_ns
        previous_odometry_x = self._last_odometry_x_m
        previous_odometry_y = self._last_odometry_y_m
        previous_odometry_yaw = self._last_odometry_yaw_rad
        self._last_odometry_timestamp_ns = timestamp_ns
        self._last_odometry_sequence = odometry.header.sequence
        self._last_odometry_x_m = odometry.x_m
        self._last_odometry_y_m = odometry.y_m
        self._last_odometry_yaw_rad = odometry.yaw_rad

        imu_used = False
        imu_rejection = None
        fused_yaw_rate = odometry.yaw_rate_radps
        if (
            previous_timestamp_ns is None
            or previous_odometry_x is None
            or previous_odometry_y is None
            or previous_odometry_yaw is None
        ):
            self._x_m = odometry.x_m
            self._y_m = odometry.y_m
            self._yaw_rad = odometry.yaw_rad
        else:
            dt_seconds = (timestamp_ns - previous_timestamp_ns) / 1_000_000_000
            odometry_delta_yaw = self._normalize_angle(
                odometry.yaw_rad - previous_odometry_yaw
            )
            odometry_midpoint_yaw = previous_odometry_yaw + odometry_delta_yaw / 2
            odometry_delta_x = odometry.x_m - previous_odometry_x
            odometry_delta_y = odometry.y_m - previous_odometry_y
            # Project the raw pose displacement onto its midpoint heading. This
            # preserves signed distance if the bounded subscriber drops one or
            # more high-rate odometry messages; using only the latest velocity
            # would permanently lose the skipped motion.
            distance_m = odometry_delta_x * math.cos(
                odometry_midpoint_yaw
            ) + odometry_delta_y * math.sin(odometry_midpoint_yaw)
            imu_delta_yaw = 0.0
            if imu is not None:
                imu_age_ns = timestamp_ns - imu.header.timestamp_monotonic_ns
                if imu_age_ns < 0:
                    imu_rejection = "IMU observation is from the future"
                elif imu_age_ns > int(self.config.max_imu_age_seconds * 1_000_000_000):
                    imu_rejection = "IMU observation is stale"
                else:
                    imu_used = True
                    imu_delta_yaw = imu.angular_velocity_z_radps * dt_seconds

            weight = self.config.imu_yaw_rate_weight if imu_used else 0.0
            fused_delta_yaw = (1 - weight) * odometry_delta_yaw + weight * imu_delta_yaw
            midpoint_yaw = self._yaw_rad + fused_delta_yaw / 2
            self._x_m += distance_m * math.cos(midpoint_yaw)
            self._y_m += distance_m * math.sin(midpoint_yaw)
            self._yaw_rad = self._normalize_angle(self._yaw_rad + fused_delta_yaw)
            fused_yaw_rate = fused_delta_yaw / dt_seconds

            position_stddev = self.config.position_process_noise_m_per_meter * abs(
                distance_m
            )
            self._position_variance_m2 += position_stddev**2
            odometry_yaw_stddev = (
                self.config.odometry_heading_noise_fraction * abs(odometry_delta_yaw)
                + self.config.heading_process_noise_rad_per_second * dt_seconds
            )
            yaw_variance = ((1 - weight) * odometry_yaw_stddev) ** 2
            if imu_used:
                yaw_variance += (
                    weight * self.config.imu_yaw_rate_stddev_radps * dt_seconds
                ) ** 2
            self._yaw_variance_rad2 += yaw_variance

        correction = self._apply_observation(observation, odometry)
        fusion_mode = (
            "corrected" if correction[0] else "wheel_imu" if imu_used else "wheel"
        )
        self._output_sequence += 1
        pose = LocalizationPose2D(
            header=MessageHeader(
                sequence=self._output_sequence,
                frame_id=odometry.header.frame_id,
                timestamp_monotonic_ns=timestamp_ns,
                source_timestamp_ns=odometry.header.source_timestamp_ns,
            ),
            child_frame_id=odometry.child_frame_id,
            x_m=self._x_m,
            y_m=self._y_m,
            yaw_rad=self._yaw_rad,
            linear_speed_mps=odometry.linear_speed_mps,
            yaw_rate_radps=fused_yaw_rate,
            position_variance_m2=self._position_variance_m2,
            yaw_variance_rad2=self._yaw_variance_rad2,
            fusion_mode=fusion_mode,
            last_correction_source=self._last_correction_source,
        )
        return PoseEstimatorResult(
            pose=pose,
            imu_used=imu_used,
            imu_rejection=imu_rejection,
            correction_applied=correction[0],
            correction_rejection=correction[1],
            position_innovation_m=correction[2],
            heading_innovation_rad=correction[3],
        )

    def _apply_observation(
        self,
        observation: Optional[PoseObservation2D],
        odometry: Odometry2D,
    ) -> tuple[bool, Optional[str], Optional[float], Optional[float]]:
        if observation is None:
            return False, None, None, None
        timestamp_ns = odometry.header.timestamp_monotonic_ns
        observation_timestamp_ns = observation.header.timestamp_monotonic_ns
        if observation.header.frame_id != odometry.header.frame_id:
            return False, "pose observation frame does not match odometry", None, None
        if observation_timestamp_ns > timestamp_ns:
            return False, "pose observation is from the future", None, None
        if timestamp_ns - observation_timestamp_ns > int(
            self.config.max_pose_observation_age_seconds * 1_000_000_000
        ):
            return False, "pose observation is stale", None, None
        if (
            self._last_observation_timestamp_ns is not None
            and observation_timestamp_ns <= self._last_observation_timestamp_ns
        ):
            return False, "pose observation timestamp must increase", None, None

        innovation_x = observation.x_m - self._x_m
        innovation_y = observation.y_m - self._y_m
        innovation_yaw = self._normalize_angle(observation.yaw_rad - self._yaw_rad)
        position_gain = self._kalman_gain(
            self._position_variance_m2,
            observation.position_variance_m2,
        )
        yaw_gain = self._kalman_gain(
            self._yaw_variance_rad2,
            observation.yaw_variance_rad2,
        )
        self._x_m += position_gain * innovation_x
        self._y_m += position_gain * innovation_y
        self._yaw_rad = self._normalize_angle(self._yaw_rad + yaw_gain * innovation_yaw)
        self._position_variance_m2 *= 1 - position_gain
        self._yaw_variance_rad2 *= 1 - yaw_gain
        self._last_observation_timestamp_ns = observation_timestamp_ns
        self._last_correction_source = observation.source
        return (
            True,
            None,
            math.hypot(innovation_x, innovation_y),
            abs(innovation_yaw),
        )

    @staticmethod
    def _kalman_gain(prior_variance: float, observation_variance: float) -> float:
        denominator = prior_variance + observation_variance
        return prior_variance / denominator if denominator else 0.0

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2 * math.pi) - math.pi


class PoseEstimatorService:
    """Consume odometry/IMU/correction topics and publish fused pose."""

    def __init__(self, bus: TopicBus, estimator: PoseEstimator) -> None:
        self._bus = bus
        self._estimator = estimator
        self._odometry_subscription: Optional[TopicSubscription[Odometry2D]] = None
        self._imu_subscription: Optional[TopicSubscription[ImuData]] = None
        self._observation_subscription: Optional[
            TopicSubscription[PoseObservation2D]
        ] = None
        self._tasks: tuple[asyncio.Task[None], ...] = ()
        self._latest_imu: Optional[ImuData] = None
        self._pending_observation: Optional[PoseObservation2D] = None
        self.latest: Optional[LocalizationPose2D] = None
        self.last_error: Optional[Exception] = None
        self.published_updates = 0
        self.imu_updates_used = 0
        self.imu_updates_rejected = 0
        self.corrections_applied = 0
        self.corrections_rejected = 0
        self.last_position_innovation_m: Optional[float] = None
        self.last_heading_innovation_rad: Optional[float] = None

    @property
    def running(self) -> bool:
        return bool(self._tasks) and all(not task.done() for task in self._tasks)

    @property
    def config(self) -> PoseEstimatorConfig:
        return self._estimator.config

    def start(self) -> None:
        if self.running:
            return
        self._odometry_subscription = self._bus.subscribe(
            ODOMETRY,
            max_queue_size=32,
            replay_latest=False,
        )
        self._imu_subscription = self._bus.subscribe(
            IMU_DATA,
            max_queue_size=1,
            replay_latest=True,
        )
        self._observation_subscription = self._bus.subscribe(
            POSE_OBSERVATION,
            max_queue_size=1,
            replay_latest=False,
        )
        retained_imu = self._bus.latest(IMU_DATA)
        if retained_imu is not None:
            self._latest_imu = retained_imu
        self._tasks = (
            asyncio.create_task(self._consume_imu(), name="pose-estimator-imu"),
            asyncio.create_task(
                self._consume_observations(), name="pose-estimator-observations"
            ),
            asyncio.create_task(
                self._consume_odometry(), name="pose-estimator-odometry"
            ),
        )

    async def stop(self) -> None:
        for subscription in (
            self._odometry_subscription,
            self._imu_subscription,
            self._observation_subscription,
        ):
            if subscription is not None:
                subscription.close()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = ()
        self._odometry_subscription = None
        self._imu_subscription = None
        self._observation_subscription = None

    def reset(self) -> None:
        self._estimator.reset()
        self._latest_imu = self._bus.latest(IMU_DATA)
        self._pending_observation = None
        self.latest = None
        self.last_error = None
        self.published_updates = 0
        self.imu_updates_used = 0
        self.imu_updates_rejected = 0
        self.corrections_applied = 0
        self.corrections_rejected = 0
        self.last_position_innovation_m = None
        self.last_heading_innovation_rad = None

    async def _consume_imu(self) -> None:
        subscription = self._imu_subscription
        if subscription is None:
            return
        async for imu in subscription:
            self._latest_imu = imu

    async def _consume_observations(self) -> None:
        subscription = self._observation_subscription
        if subscription is None:
            return
        async for observation in subscription:
            self._pending_observation = observation

    async def _consume_odometry(self) -> None:
        subscription = self._odometry_subscription
        if subscription is None:
            return
        async for odometry in subscription:
            imu = self._latest_imu or self._bus.latest(IMU_DATA)
            observation = self._pending_observation
            observation_is_due = bool(
                observation is not None
                and observation.header.timestamp_monotonic_ns
                <= odometry.header.timestamp_monotonic_ns
            )
            if observation_is_due:
                self._pending_observation = None
            else:
                # A correction can arrive between two odometry samples. Keep it
                # until the estimator reaches its timestamp instead of counting
                # it as an invalid future measurement on every update.
                observation = None
            try:
                result = self._estimator.update(
                    odometry,
                    imu=imu,
                    observation=observation,
                )
            except PoseEstimationInputError as error:
                self.last_error = error
                continue
            if result.imu_used:
                self.imu_updates_used += 1
            elif result.imu_rejection is not None:
                self.imu_updates_rejected += 1
            if result.correction_applied:
                self.corrections_applied += 1
                self.last_position_innovation_m = result.position_innovation_m
                self.last_heading_innovation_rad = result.heading_innovation_rad
            elif result.correction_rejection is not None:
                self.corrections_rejected += 1
            self._bus.publish(LOCALIZATION_POSE, result.pose)
            self.latest = result.pose
            self.last_error = None
            self.published_updates += 1


class PoseEstimatorSupervisor:
    """Stable hot-reloadable lifecycle handle for optional pose fusion."""

    def __init__(self, service: Optional[PoseEstimatorService] = None) -> None:
        self._service = service
        self._started = False
        self._lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return self._service is not None

    @property
    def running(self) -> bool:
        return self._service is not None and self._service.running

    @property
    def service(self) -> Optional[PoseEstimatorService]:
        return self._service

    async def start(self) -> None:
        async with self._lock:
            self._started = True
            if self._service is not None:
                self._service.start()

    async def stop(self) -> None:
        async with self._lock:
            self._started = False
            if self._service is not None:
                await self._service.stop()

    async def reconfigure(self, service: Optional[PoseEstimatorService]) -> None:
        async with self._lock:
            if self._service is not None:
                await self._service.stop()
            self._service = service
            if self._started and self._service is not None:
                self._service.start()

    async def reconfigure_from(self, replacement: "PoseEstimatorSupervisor") -> None:
        await self.reconfigure(replacement._service)

    async def reset(self) -> None:
        async with self._lock:
            service = self._service
            if service is None:
                return
            service.reset()


__all__ = [
    "PoseEstimationInputError",
    "PoseEstimator",
    "PoseEstimatorConfig",
    "PoseEstimatorResult",
    "PoseEstimatorService",
    "PoseEstimatorSupervisor",
]
