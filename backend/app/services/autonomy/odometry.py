"""Hardware-neutral Ackermann odometry estimation and topic integration."""

import asyncio
import math
from dataclasses import dataclass
from typing import Optional

from app.schemas.autonomy import EncoderState, MessageHeader, Odometry2D, SteeringState
from app.services.autonomy.topic_bus import TopicBus, TopicSubscription
from app.services.autonomy.topics import ENCODER_STATE, ODOMETRY, STEERING_STATE


class OdometryInputError(ValueError):
    """Raised when ordered encoder/steering inputs cannot form safe odometry."""


@dataclass(frozen=True)
class AckermannOdometryConfig:
    wheelbase_m: float
    wheel_radius_m: float
    encoder_ticks_per_revolution: int
    gear_ratio: float = 1.0
    max_steering_age_seconds: float = 0.25

    def __post_init__(self) -> None:
        if not math.isfinite(self.wheelbase_m) or self.wheelbase_m <= 0:
            raise ValueError("wheelbase_m must be finite and greater than zero")
        if not math.isfinite(self.wheel_radius_m) or self.wheel_radius_m <= 0:
            raise ValueError("wheel_radius_m must be finite and greater than zero")
        if self.encoder_ticks_per_revolution <= 0:
            raise ValueError("encoder_ticks_per_revolution must be greater than zero")
        if not math.isfinite(self.gear_ratio) or self.gear_ratio <= 0:
            raise ValueError("gear_ratio must be finite and greater than zero")
        if (
            not math.isfinite(self.max_steering_age_seconds)
            or self.max_steering_age_seconds <= 0
        ):
            raise ValueError(
                "max_steering_age_seconds must be finite and greater than zero"
            )


class AckermannOdometryEstimator:
    """Integrate signed encoder deltas using the planar bicycle model."""

    def __init__(self, config: AckermannOdometryConfig) -> None:
        self.config = config
        self.reset()

    def reset(
        self, *, x_m: float = 0.0, y_m: float = 0.0, yaw_rad: float = 0.0
    ) -> None:
        for name, value in [("x_m", x_m), ("y_m", y_m), ("yaw_rad", yaw_rad)]:
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        self._x_m = x_m
        self._y_m = y_m
        self._yaw_rad = self._normalize_angle(yaw_rad)
        self._last_encoder_timestamp_ns: Optional[int] = None
        self._last_encoder_sequence: Optional[int] = None
        self._output_sequence = 0

    def update(
        self,
        encoder: EncoderState,
        steering: SteeringState,
    ) -> Odometry2D:
        """Consume one ordered encoder sample and the latest fresh steering state."""

        timestamp = encoder.header.timestamp_monotonic_ns
        if (
            self._last_encoder_sequence is not None
            and encoder.header.sequence <= self._last_encoder_sequence
        ):
            raise OdometryInputError("encoder sequence must increase monotonically")
        if (
            self._last_encoder_timestamp_ns is not None
            and timestamp <= self._last_encoder_timestamp_ns
        ):
            raise OdometryInputError("encoder timestamp must increase monotonically")

        steering_timestamp = steering.header.timestamp_monotonic_ns
        if steering_timestamp > timestamp:
            raise OdometryInputError("steering observation cannot be from the future")
        steering_age_ns = timestamp - steering_timestamp
        maximum_age_ns = int(self.config.max_steering_age_seconds * 1_000_000_000)
        if steering_age_ns > maximum_age_ns:
            raise OdometryInputError("steering observation is stale")

        self._last_encoder_sequence = encoder.header.sequence
        previous_timestamp = self._last_encoder_timestamp_ns
        self._last_encoder_timestamp_ns = timestamp
        if previous_timestamp is None:
            return self._message(
                encoder,
                linear_speed_mps=0.0,
                yaw_rate_radps=0.0,
            )

        dt_seconds = (timestamp - previous_timestamp) / 1_000_000_000
        wheel_revolutions = (
            encoder.mean_delta_ticks
            / self.config.encoder_ticks_per_revolution
            / self.config.gear_ratio
        )
        distance_m = wheel_revolutions * 2 * math.pi * self.config.wheel_radius_m
        steering_angle = (
            steering.measured_angle_rad
            if steering.measured_angle_rad is not None
            else steering.commanded_angle_rad
        )
        delta_yaw = distance_m / self.config.wheelbase_m * math.tan(steering_angle)
        midpoint_yaw = self._yaw_rad + delta_yaw / 2
        self._x_m += distance_m * math.cos(midpoint_yaw)
        self._y_m += distance_m * math.sin(midpoint_yaw)
        self._yaw_rad = self._normalize_angle(self._yaw_rad + delta_yaw)

        return self._message(
            encoder,
            linear_speed_mps=distance_m / dt_seconds,
            yaw_rate_radps=delta_yaw / dt_seconds,
        )

    def _message(
        self,
        encoder: EncoderState,
        *,
        linear_speed_mps: float,
        yaw_rate_radps: float,
    ) -> Odometry2D:
        self._output_sequence += 1
        return Odometry2D(
            header=MessageHeader(
                sequence=self._output_sequence,
                frame_id="odom",
                timestamp_monotonic_ns=encoder.header.timestamp_monotonic_ns,
                source_timestamp_ns=encoder.header.source_timestamp_ns,
            ),
            child_frame_id="base_link",
            x_m=self._x_m,
            y_m=self._y_m,
            yaw_rad=self._yaw_rad,
            linear_speed_mps=linear_speed_mps,
            yaw_rate_radps=yaw_rate_radps,
        )

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2 * math.pi) - math.pi


class AckermannOdometryService:
    """Consume encoder/steering topics and publish planar odometry."""

    def __init__(self, bus: TopicBus, estimator: AckermannOdometryEstimator) -> None:
        self._bus = bus
        self._estimator = estimator
        self._encoder_subscription: Optional[TopicSubscription[EncoderState]] = None
        self._steering_subscription: Optional[TopicSubscription[SteeringState]] = None
        self._encoder_task: Optional[asyncio.Task[None]] = None
        self._steering_task: Optional[asyncio.Task[None]] = None
        self._latest_steering: Optional[SteeringState] = None
        self.last_error: Optional[OdometryInputError] = None
        self.published_updates = 0
        self.skipped_updates = 0

    @property
    def running(self) -> bool:
        tasks = (self._encoder_task, self._steering_task)
        return all(task is not None and not task.done() for task in tasks)

    def start(self) -> None:
        if self.running:
            return
        self._steering_subscription = self._bus.subscribe(
            STEERING_STATE,
            max_queue_size=1,
            replay_latest=True,
        )
        self._encoder_subscription = self._bus.subscribe(
            ENCODER_STATE,
            max_queue_size=32,
            replay_latest=False,
        )
        retained_steering = self._bus.latest(STEERING_STATE)
        if retained_steering is not None:
            self._latest_steering = retained_steering
        self._steering_task = asyncio.create_task(
            self._consume_steering(),
            name="odometry-steering-consumer",
        )
        self._encoder_task = asyncio.create_task(
            self._consume_encoder(),
            name="odometry-encoder-consumer",
        )

    async def stop(self) -> None:
        subscriptions = (self._encoder_subscription, self._steering_subscription)
        for subscription in subscriptions:
            if subscription:
                subscription.close()
        tasks = tuple(
            task
            for task in (self._encoder_task, self._steering_task)
            if task is not None
        )
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._encoder_subscription = None
        self._steering_subscription = None
        self._encoder_task = None
        self._steering_task = None

    def reconfigure(self, config: AckermannOdometryConfig) -> None:
        """Apply new geometry atomically and start a fresh odometry origin."""

        self._estimator = AckermannOdometryEstimator(config)
        self._latest_steering = self._bus.latest(STEERING_STATE)
        self.last_error = None

    def reset(self) -> None:
        """Reset pose and input ordering while preserving calibrated geometry."""

        self._estimator.reset()
        self._latest_steering = self._bus.latest(STEERING_STATE)
        self.last_error = None

    async def _consume_steering(self) -> None:
        subscription = self._steering_subscription
        if subscription is None:
            return
        async for steering in subscription:
            self._latest_steering = steering

    async def _consume_encoder(self) -> None:
        subscription = self._encoder_subscription
        if subscription is None:
            return
        async for encoder in subscription:
            steering = self._latest_steering or self._bus.latest(STEERING_STATE)
            if steering is None:
                self.skipped_updates += 1
                continue
            try:
                odometry = self._estimator.update(encoder, steering)
            except OdometryInputError as error:
                self.last_error = error
                self.skipped_updates += 1
                continue
            self.last_error = None
            self._bus.publish(ODOMETRY, odometry)
            self.published_updates += 1


__all__ = [
    "AckermannOdometryConfig",
    "AckermannOdometryEstimator",
    "AckermannOdometryService",
    "OdometryInputError",
]
