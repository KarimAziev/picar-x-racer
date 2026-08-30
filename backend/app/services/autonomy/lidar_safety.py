"""Fail-safe front-sector LiDAR constraints for the motion arbiter."""

import asyncio
import math
from dataclasses import dataclass
from typing import Optional, Protocol

from app.core.px_logger import Logger
from app.schemas.autonomy import LaserScan, MessageHeader, SafetyState
from app.services.autonomy.clock import Clock, SystemClock
from app.services.autonomy.messages import SafetyConstraint, SafetySeverity
from app.services.autonomy.topic_bus import (
    SubscriptionClosed,
    TopicBus,
    TopicSubscription,
)
from app.services.autonomy.topics import LIDAR_SCAN, SAFETY_STATE


_log = Logger(__name__)
_CONSTRAINT_ID = "lidar-front-zone"


class SafetyConstraintSink(Protocol):
    def put_constraint(self, constraint: SafetyConstraint) -> None: ...

    def remove_constraint(self, constraint_id: str) -> None: ...


@dataclass(frozen=True)
class LidarSafetyZone:
    front_half_angle_rad: float
    stop_distance_m: float
    slow_distance_m: float
    max_forward_speed_mps: float
    sensor_x_m: float = 0.0
    sensor_y_m: float = 0.0
    sensor_yaw_rad: float = 0.0
    min_obstacle_points: int = 2

    def __post_init__(self) -> None:
        finite_values = (
            self.front_half_angle_rad,
            self.stop_distance_m,
            self.slow_distance_m,
            self.max_forward_speed_mps,
            self.sensor_x_m,
            self.sensor_y_m,
            self.sensor_yaw_rad,
        )
        if not all(math.isfinite(value) for value in finite_values):
            raise ValueError("LiDAR safety geometry must be finite")
        if not 0 < self.front_half_angle_rad <= math.pi / 2:
            raise ValueError("front_half_angle_rad must be in (0, pi/2]")
        if self.stop_distance_m <= 0:
            raise ValueError("stop_distance_m must be greater than zero")
        if self.slow_distance_m <= self.stop_distance_m:
            raise ValueError("slow_distance_m must exceed stop_distance_m")
        if self.max_forward_speed_mps <= 0:
            raise ValueError("max_forward_speed_mps must be greater than zero")
        if self.min_obstacle_points <= 0:
            raise ValueError("min_obstacle_points must be greater than zero")


@dataclass(frozen=True)
class LidarSafetyDecision:
    max_forward_speed_mps: float
    nearest_obstacle_m: Optional[float]
    considered_points: int
    reason: Optional[str]

    @property
    def forward_blocked(self) -> bool:
        return self.max_forward_speed_mps == 0.0


class LidarSafetyEvaluator:
    def __init__(self, zone: LidarSafetyZone) -> None:
        self.zone = zone

    def evaluate(self, scan: LaserScan) -> LidarSafetyDecision:
        distances = self._front_sector_distances(scan)
        if len(distances) < self.zone.min_obstacle_points:
            return LidarSafetyDecision(
                max_forward_speed_mps=self.zone.max_forward_speed_mps,
                nearest_obstacle_m=None,
                considered_points=len(distances),
                reason=None,
            )

        distances.sort()
        confirmed_distance = distances[self.zone.min_obstacle_points - 1]
        if confirmed_distance <= self.zone.stop_distance_m:
            return LidarSafetyDecision(
                max_forward_speed_mps=0.0,
                nearest_obstacle_m=confirmed_distance,
                considered_points=len(distances),
                reason=f"forward obstacle at {confirmed_distance:.3f} m",
            )
        if confirmed_distance < self.zone.slow_distance_m:
            span = self.zone.slow_distance_m - self.zone.stop_distance_m
            ratio = (confirmed_distance - self.zone.stop_distance_m) / span
            speed = self.zone.max_forward_speed_mps * ratio
            return LidarSafetyDecision(
                max_forward_speed_mps=speed,
                nearest_obstacle_m=confirmed_distance,
                considered_points=len(distances),
                reason=f"forward obstacle nearby at {confirmed_distance:.3f} m",
            )
        return LidarSafetyDecision(
            max_forward_speed_mps=self.zone.max_forward_speed_mps,
            nearest_obstacle_m=confirmed_distance,
            considered_points=len(distances),
            reason=None,
        )

    def _front_sector_distances(self, scan: LaserScan) -> list[float]:
        distances = []
        cos_yaw = math.cos(self.zone.sensor_yaw_rad)
        sin_yaw = math.sin(self.zone.sensor_yaw_rad)
        for index, distance in enumerate(scan.ranges_m):
            if (
                not math.isfinite(distance)
                or distance < scan.range_min_m
                or distance > scan.range_max_m
            ):
                continue
            sensor_angle = scan.angle_min_rad + index * scan.angle_increment_rad
            sensor_x = distance * math.cos(sensor_angle)
            sensor_y = distance * math.sin(sensor_angle)
            base_x = self.zone.sensor_x_m + cos_yaw * sensor_x - sin_yaw * sensor_y
            base_y = self.zone.sensor_y_m + sin_yaw * sensor_x + cos_yaw * sensor_y
            if base_x <= 0:
                continue
            base_angle = math.atan2(base_y, base_x)
            if abs(base_angle) <= self.zone.front_half_angle_rad:
                distances.append(math.hypot(base_x, base_y))
        return distances


class LidarSafetyService:
    """Translate fresh LiDAR scans into directional arbiter constraints."""

    def __init__(
        self,
        bus: TopicBus,
        motion_control: SafetyConstraintSink,
        evaluator: LidarSafetyEvaluator,
        *,
        scan_timeout_seconds: float,
        clock: Optional[Clock] = None,
    ) -> None:
        if scan_timeout_seconds <= 0:
            raise ValueError("scan_timeout_seconds must be greater than zero")
        self._bus = bus
        self._motion_control = motion_control
        self._evaluator = evaluator
        self._scan_timeout_seconds = scan_timeout_seconds
        self._clock = clock or SystemClock()
        self._subscription: Optional[TopicSubscription[LaserScan]] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._sequence = 0
        self._last_state: Optional[SafetyState] = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    @property
    def last_state(self) -> Optional[SafetyState]:
        return self._last_state

    def start(self) -> None:
        if self.running:
            return
        self._subscription = self._bus.subscribe(
            LIDAR_SCAN,
            max_queue_size=1,
            replay_latest=True,
        )
        self._apply_block("waiting for a fresh LiDAR scan")
        self._task = asyncio.create_task(
            self._run(),
            name="lidar-forward-safety",
        )

    async def stop(self) -> None:
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
        if task is not None:
            await asyncio.gather(task, return_exceptions=True)
        if self._subscription is not None:
            self._subscription.close()
            self._subscription = None
        self._apply_block("LiDAR safety service is stopped")

    def reconfigure(
        self,
        evaluator: LidarSafetyEvaluator,
        *,
        scan_timeout_seconds: float,
    ) -> None:
        """Apply validated safety geometry without replacing topic consumers."""

        if scan_timeout_seconds <= 0:
            raise ValueError("scan_timeout_seconds must be greater than zero")
        self._evaluator = evaluator
        self._scan_timeout_seconds = scan_timeout_seconds
        self._apply_block("waiting for a fresh LiDAR scan after reconfiguration")

    def reconfigure_from(self, replacement: "LidarSafetyService") -> None:
        self.reconfigure(
            replacement._evaluator,
            scan_timeout_seconds=replacement._scan_timeout_seconds,
        )

    async def _run(self) -> None:
        subscription = self._subscription
        if subscription is None:
            return
        while True:
            try:
                scan = await asyncio.wait_for(
                    subscription.get(),
                    timeout=self._scan_timeout_seconds,
                )
                self._apply_decision(scan, self._evaluator.evaluate(scan))
            except asyncio.TimeoutError:
                self._apply_block("LiDAR scan is stale")
            except SubscriptionClosed:
                self._apply_block("LiDAR scan stream is closed")
                return
            except asyncio.CancelledError:
                raise
            except Exception as error:
                _log.error("LiDAR safety evaluation failed: %s", error)
                self._apply_block(f"LiDAR safety error: {error}")

    def _apply_decision(
        self,
        scan: LaserScan,
        decision: LidarSafetyDecision,
    ) -> None:
        now = self._clock.monotonic_ns()
        if decision.max_forward_speed_mps < self._evaluator.zone.max_forward_speed_mps:
            self._motion_control.put_constraint(
                SafetyConstraint(
                    constraint_id=_CONSTRAINT_ID,
                    source="lidar-safety",
                    severity=SafetySeverity.LIMIT,
                    created_monotonic_ns=now,
                    reason=decision.reason or "LiDAR forward speed limit",
                    max_forward_speed_mps=decision.max_forward_speed_mps,
                )
            )
        else:
            self._motion_control.remove_constraint(_CONSTRAINT_ID)
        self._publish_state(
            now=now,
            frame_id=scan.header.frame_id,
            source_timestamp_ns=scan.header.timestamp_monotonic_ns,
            decision=decision,
        )

    def _apply_block(self, reason: str) -> None:
        now = self._clock.monotonic_ns()
        self._motion_control.put_constraint(
            SafetyConstraint(
                constraint_id=_CONSTRAINT_ID,
                source="lidar-safety",
                severity=SafetySeverity.LIMIT,
                created_monotonic_ns=now,
                reason=reason,
                max_forward_speed_mps=0.0,
            )
        )
        self._publish_state(
            now=now,
            frame_id="base_link",
            source_timestamp_ns=None,
            decision=LidarSafetyDecision(
                max_forward_speed_mps=0.0,
                nearest_obstacle_m=None,
                considered_points=0,
                reason=reason,
            ),
        )

    def _publish_state(
        self,
        *,
        now: int,
        frame_id: str,
        source_timestamp_ns: Optional[int],
        decision: LidarSafetyDecision,
    ) -> None:
        self._sequence += 1
        state = SafetyState(
            header=MessageHeader(
                sequence=self._sequence,
                frame_id=frame_id,
                timestamp_monotonic_ns=now,
                source_timestamp_ns=source_timestamp_ns,
            ),
            forward_blocked=decision.forward_blocked,
            max_forward_speed_mps=decision.max_forward_speed_mps,
            nearest_obstacle_m=decision.nearest_obstacle_m,
            considered_points=decision.considered_points,
            reason=decision.reason,
        )
        self._last_state = state
        self._bus.publish(SAFETY_STATE, state)


__all__ = [
    "LidarSafetyDecision",
    "LidarSafetyEvaluator",
    "LidarSafetyService",
    "LidarSafetyZone",
    "SafetyConstraintSink",
]
