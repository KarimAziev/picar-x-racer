"""Deterministic 2D LiDAR scan matching against a configured known world."""

import asyncio
import math
from dataclasses import dataclass
from typing import Literal, Optional, Sequence, Tuple

from app.schemas.autonomy import (
    LaserScan,
    LocalizationPose2D,
    MessageHeader,
    PoseObservation2D,
)
from app.services.autonomy.local_mapping import StaticTransform2D
from app.services.autonomy.simulation_world import SimulationWorld
from app.services.autonomy.topic_bus import (
    SubscriptionClosed,
    TopicBus,
    TopicSubscription,
)
from app.services.autonomy.topics import LIDAR_SCAN, LOCALIZATION_POSE, POSE_OBSERVATION


ScanMatchRejection = Literal["insufficient_points", "poor_quality"]


@dataclass(frozen=True)
class KnownWorldScanMatcherConfig:
    odom_origin_in_world: Tuple[float, float, float]
    sensor_transform: StaticTransform2D = StaticTransform2D()
    expected_scan_frame_id: str = "lidar"
    search_translation_m: float = 0.15
    search_heading_rad: float = math.radians(8)
    coarse_translation_step_m: float = 0.05
    coarse_heading_step_rad: float = math.radians(2)
    refinement_translation_step_m: float = 0.01
    refinement_heading_step_rad: float = math.radians(0.5)
    max_scan_points: int = 48
    min_valid_points: int = 16
    max_mean_error_m: float = 0.08
    max_residual_m: float = 0.5
    position_stddev_m: float = 0.03
    heading_stddev_rad: float = math.radians(1.5)
    source: str = "simulation_known_world_scan_matcher"

    def __post_init__(self) -> None:
        numeric_values = (
            *self.odom_origin_in_world,
            self.sensor_transform.x_m,
            self.sensor_transform.y_m,
            self.sensor_transform.yaw_rad,
            self.search_translation_m,
            self.search_heading_rad,
            self.coarse_translation_step_m,
            self.coarse_heading_step_rad,
            self.refinement_translation_step_m,
            self.refinement_heading_step_rad,
            self.max_mean_error_m,
            self.max_residual_m,
            self.position_stddev_m,
            self.heading_stddev_rad,
        )
        if not all(math.isfinite(value) for value in numeric_values):
            raise ValueError("scan matcher configuration must be finite")
        if len(self.odom_origin_in_world) != 3:
            raise ValueError("odom_origin_in_world must contain x, y, and yaw")
        if not self.expected_scan_frame_id.strip() or not self.source.strip():
            raise ValueError("scan matcher frame and source must not be empty")
        positive_values = (
            self.search_translation_m,
            self.search_heading_rad,
            self.coarse_translation_step_m,
            self.coarse_heading_step_rad,
            self.refinement_translation_step_m,
            self.refinement_heading_step_rad,
            self.max_mean_error_m,
            self.max_residual_m,
            self.position_stddev_m,
            self.heading_stddev_rad,
        )
        if any(value <= 0 for value in positive_values):
            raise ValueError(
                "scan matcher search and uncertainty values must be positive"
            )
        if self.min_valid_points < 3 or self.max_scan_points < self.min_valid_points:
            raise ValueError("scan matcher point limits are invalid")
        if self.refinement_translation_step_m > self.coarse_translation_step_m:
            raise ValueError("translation refinement step exceeds coarse step")
        if self.refinement_heading_step_rad > self.coarse_heading_step_rad:
            raise ValueError("heading refinement step exceeds coarse step")


@dataclass(frozen=True)
class ScanMatchResult:
    observation: Optional[PoseObservation2D]
    rejection: Optional[ScanMatchRejection]
    valid_points: int
    candidates_evaluated: int
    mean_error_m: Optional[float]
    prior_mean_error_m: Optional[float]

    @property
    def accepted(self) -> bool:
        return self.observation is not None


class KnownWorldScanMatcher:
    """Align range endpoints to line segments with a bounded local grid search."""

    def __init__(
        self, world: SimulationWorld, config: KnownWorldScanMatcherConfig
    ) -> None:
        self.world = world
        self.config = config

    def match(
        self,
        scan: LaserScan,
        prior: LocalizationPose2D,
        *,
        sequence: int,
    ) -> ScanMatchResult:
        if scan.header.frame_id != self.config.expected_scan_frame_id:
            raise ValueError(
                f"scan frame {scan.header.frame_id!r} does not match "
                f"{self.config.expected_scan_frame_id!r}"
            )
        points = self._sample_base_points(scan)
        if len(points) < self.config.min_valid_points:
            return ScanMatchResult(
                observation=None,
                rejection="insufficient_points",
                valid_points=len(points),
                candidates_evaluated=0,
                mean_error_m=None,
                prior_mean_error_m=None,
            )

        prior_pose = (prior.x_m, prior.y_m, prior.yaw_rad)
        prior_score = self._score(prior_pose, points)
        coarse_offsets = self._candidate_offsets(
            self.config.search_translation_m,
            self.config.coarse_translation_step_m,
            self.config.search_heading_rad,
            self.config.coarse_heading_step_rad,
        )
        best_pose, best_score = self._best_candidate(prior_pose, points, coarse_offsets)
        refinement_offsets = self._candidate_offsets(
            (
                self.config.coarse_translation_step_m
                + self.config.refinement_translation_step_m
            )
            / 2,
            self.config.refinement_translation_step_m,
            (
                self.config.coarse_heading_step_rad
                + self.config.refinement_heading_step_rad
            )
            / 2,
            self.config.refinement_heading_step_rad,
        )
        refined_pose, refined_score = self._best_candidate(
            best_pose, points, refinement_offsets, tie_origin=prior_pose
        )
        candidates_evaluated = len(coarse_offsets) + len(refinement_offsets)
        if refined_score > self.config.max_mean_error_m:
            return ScanMatchResult(
                observation=None,
                rejection="poor_quality",
                valid_points=len(points),
                candidates_evaluated=candidates_evaluated,
                mean_error_m=refined_score,
                prior_mean_error_m=prior_score,
            )
        observation = PoseObservation2D(
            header=MessageHeader(
                sequence=sequence,
                frame_id=prior.header.frame_id,
                timestamp_monotonic_ns=scan.header.timestamp_monotonic_ns,
                source_timestamp_ns=scan.header.source_timestamp_ns,
            ),
            x_m=refined_pose[0],
            y_m=refined_pose[1],
            yaw_rad=self._normalize_angle(refined_pose[2]),
            position_variance_m2=self.config.position_stddev_m**2,
            yaw_variance_rad2=self.config.heading_stddev_rad**2,
            source=self.config.source,
        )
        return ScanMatchResult(
            observation=observation,
            rejection=None,
            valid_points=len(points),
            candidates_evaluated=candidates_evaluated,
            mean_error_m=refined_score,
            prior_mean_error_m=prior_score,
        )

    def _sample_base_points(self, scan: LaserScan) -> Tuple[Tuple[float, float], ...]:
        valid = [
            (index, distance)
            for index, distance in enumerate(scan.ranges_m)
            if math.isfinite(distance)
            and scan.range_min_m <= distance <= scan.range_max_m
        ]
        if len(valid) > self.config.max_scan_points:
            count = self.config.max_scan_points
            valid = [
                valid[round(index * (len(valid) - 1) / (count - 1))]
                for index in range(count)
            ]
        transform = self.config.sensor_transform
        cos_sensor = math.cos(transform.yaw_rad)
        sin_sensor = math.sin(transform.yaw_rad)
        points = []
        for index, distance in valid:
            angle = scan.angle_min_rad + index * scan.angle_increment_rad
            scan_x = distance * math.cos(angle)
            scan_y = distance * math.sin(angle)
            points.append(
                (
                    transform.x_m + cos_sensor * scan_x - sin_sensor * scan_y,
                    transform.y_m + sin_sensor * scan_x + cos_sensor * scan_y,
                )
            )
        return tuple(points)

    def _score(
        self,
        pose_in_odom: Tuple[float, float, float],
        points_in_base: Sequence[Tuple[float, float]],
    ) -> float:
        world_x, world_y, world_yaw = self._odom_pose_to_world(pose_in_odom)
        cos_yaw = math.cos(world_yaw)
        sin_yaw = math.sin(world_yaw)
        total = 0.0
        for point_x, point_y in points_in_base:
            endpoint_x = world_x + cos_yaw * point_x - sin_yaw * point_y
            endpoint_y = world_y + sin_yaw * point_x + cos_yaw * point_y
            total += min(
                self.config.max_residual_m,
                self.world.distance_to_nearest_segment(endpoint_x, endpoint_y),
            )
        return total / len(points_in_base)

    def _odom_pose_to_world(
        self, pose: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        origin_x, origin_y, origin_yaw = self.config.odom_origin_in_world
        cos_origin = math.cos(origin_yaw)
        sin_origin = math.sin(origin_yaw)
        return (
            origin_x + cos_origin * pose[0] - sin_origin * pose[1],
            origin_y + sin_origin * pose[0] + cos_origin * pose[1],
            origin_yaw + pose[2],
        )

    def _best_candidate(
        self,
        center: Tuple[float, float, float],
        points: Sequence[Tuple[float, float]],
        offsets: Sequence[Tuple[float, float, float]],
        *,
        tie_origin: Optional[Tuple[float, float, float]] = None,
    ) -> Tuple[Tuple[float, float, float], float]:
        origin = tie_origin or center
        best_pose = center
        best_key = (math.inf, math.inf, math.inf, math.inf, math.inf)
        for dx, dy, dyaw in offsets:
            pose = (center[0] + dx, center[1] + dy, center[2] + dyaw)
            score = self._score(pose, points)
            displacement = math.hypot(pose[0] - origin[0], pose[1] - origin[1])
            heading_delta = abs(self._normalize_angle(pose[2] - origin[2]))
            key = (score, displacement, heading_delta, pose[0], pose[1])
            if key < best_key:
                best_key = key
                best_pose = pose
        return best_pose, best_key[0]

    @staticmethod
    def _axis_offsets(span: float, step: float) -> Tuple[float, ...]:
        steps = max(1, math.floor(span / step + 1e-9))
        return tuple(index * step for index in range(-steps, steps + 1))

    @classmethod
    def _candidate_offsets(
        cls,
        translation_span: float,
        translation_step: float,
        heading_span: float,
        heading_step: float,
    ) -> Tuple[Tuple[float, float, float], ...]:
        translations = cls._axis_offsets(translation_span, translation_step)
        headings = cls._axis_offsets(heading_span, heading_step)
        return tuple(
            (dx, dy, dyaw)
            for dx in translations
            for dy in translations
            for dyaw in headings
        )

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2 * math.pi) - math.pi


class KnownWorldScanMatcherService:
    """Match each fresh scan to the latest fused pose and publish corrections."""

    def __init__(
        self,
        bus: TopicBus,
        matcher: KnownWorldScanMatcher,
        *,
        max_pose_age_seconds: float,
    ) -> None:
        if not math.isfinite(max_pose_age_seconds) or max_pose_age_seconds <= 0:
            raise ValueError("maximum pose age must be positive and finite")
        self._bus = bus
        self.matcher = matcher
        self._max_pose_age_ns = round(max_pose_age_seconds * 1_000_000_000)
        self._subscription: Optional[TopicSubscription[LaserScan]] = None
        self._task: Optional[asyncio.Task[None]] = None
        self.reset()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        if self.running:
            return
        self._subscription = self._bus.subscribe(LIDAR_SCAN, max_queue_size=1)
        self._task = asyncio.create_task(self._run(), name="known-world-scan-matcher")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        self._task = None
        if self._subscription is not None:
            self._subscription.close()
        self._subscription = None

    def reset(self) -> None:
        self.scans_received = 0
        self.matches_published = 0
        self.rejected_missing_pose = 0
        self.rejected_pose_timing = 0
        self.rejected_insufficient_points = 0
        self.rejected_quality = 0
        self.last_mean_error_m: Optional[float] = None
        self.last_prior_mean_error_m: Optional[float] = None
        self.last_valid_points = 0
        self.last_candidates_evaluated = 0
        self.latest_observation: Optional[PoseObservation2D] = None
        self.last_rejection: Optional[str] = None
        self.last_error: Optional[Exception] = None
        self._sequence = 0

    async def _run(self) -> None:
        subscription = self._subscription
        if subscription is None:
            return
        try:
            async for scan in subscription:
                self.scans_received += 1
                prior = self._bus.latest(LOCALIZATION_POSE)
                if prior is None:
                    self.rejected_missing_pose += 1
                    self.last_rejection = "no localization pose is available"
                    continue
                age_ns = (
                    scan.header.timestamp_monotonic_ns
                    - prior.header.timestamp_monotonic_ns
                )
                if age_ns < 0 or age_ns > self._max_pose_age_ns:
                    self.rejected_pose_timing += 1
                    self.last_rejection = (
                        "localization pose is from the future"
                        if age_ns < 0
                        else "localization pose is too old"
                    )
                    continue
                try:
                    result = await asyncio.to_thread(
                        self.matcher.match, scan, prior, sequence=self._sequence
                    )
                except Exception as error:
                    self.last_error = error
                    self.last_rejection = str(error)
                    continue
                self.last_valid_points = result.valid_points
                self.last_candidates_evaluated = result.candidates_evaluated
                self.last_mean_error_m = result.mean_error_m
                self.last_prior_mean_error_m = result.prior_mean_error_m
                if result.rejection == "insufficient_points":
                    self.rejected_insufficient_points += 1
                    self.last_rejection = "scan has too few finite returns"
                    continue
                if result.rejection == "poor_quality":
                    self.rejected_quality += 1
                    self.last_rejection = (
                        "best scan alignment exceeds the error threshold"
                    )
                    continue
                if result.observation is None:
                    continue
                self._bus.publish(POSE_OBSERVATION, result.observation)
                self.latest_observation = result.observation
                self.matches_published += 1
                self._sequence += 1
                self.last_rejection = None
                self.last_error = None
        except SubscriptionClosed:
            return


class KnownWorldScanMatcherSupervisor:
    """Stable hot-reloadable handle for the optional known-world matcher."""

    def __init__(self, service: Optional[KnownWorldScanMatcherService] = None) -> None:
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
    def service(self) -> Optional[KnownWorldScanMatcherService]:
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

    async def reconfigure_from(
        self, replacement: "KnownWorldScanMatcherSupervisor"
    ) -> None:
        async with self._lock:
            if self._service is not None:
                await self._service.stop()
            self._service = replacement._service
            if self._started and self._service is not None:
                self._service.start()

    async def reset(self) -> None:
        async with self._lock:
            if self._service is not None:
                self._service.reset()


__all__ = [
    "KnownWorldScanMatcher",
    "KnownWorldScanMatcherConfig",
    "KnownWorldScanMatcherService",
    "KnownWorldScanMatcherSupervisor",
    "ScanMatchResult",
]
