"""Fixed local occupancy grid built from LiDAR scans and a planar pose stream."""

import asyncio
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple, TypeVar, Union

from app.schemas.autonomy import (
    LaserScan,
    LocalizationPose2D,
    MappingPoseSource,
    MappingSessionState,
    MappingSessionStatus,
    MessageHeader,
    OccupancyGrid,
    Odometry2D,
)
from app.services.autonomy.topic_bus import (
    SubscriptionClosed,
    TopicBus,
    TopicSubscription,
)
from app.services.autonomy.topics import (
    LIDAR_SCAN,
    LOCALIZATION_POSE,
    LOCAL_MAP,
    ODOMETRY,
)


MappingPose = Union[Odometry2D, LocalizationPose2D]
MappingPoseT = TypeVar("MappingPoseT", Odometry2D, LocalizationPose2D)
_POSE_HISTORY_LIMIT = 4096


@dataclass(frozen=True)
class StaticTransform2D:
    x_m: float = 0.0
    y_m: float = 0.0
    yaw_rad: float = 0.0


@dataclass(frozen=True)
class LocalOccupancyGridConfig:
    width_m: float
    height_m: float
    resolution_m: float
    sensor_transform: StaticTransform2D = StaticTransform2D()

    def __post_init__(self) -> None:
        values = (
            self.width_m,
            self.height_m,
            self.resolution_m,
            self.sensor_transform.x_m,
            self.sensor_transform.y_m,
            self.sensor_transform.yaw_rad,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("mapping geometry must be finite")
        if self.width_m <= 0 or self.height_m <= 0 or self.resolution_m <= 0:
            raise ValueError("mapping dimensions and resolution must be positive")


class LocalOccupancyGrid:
    """Accumulate bounded integer evidence for free and occupied cells."""

    def __init__(self, config: LocalOccupancyGridConfig) -> None:
        self.config = config
        self.width = max(1, round(config.width_m / config.resolution_m))
        self.height = max(1, round(config.height_m / config.resolution_m))
        self.origin_x_m = -(self.width * config.resolution_m) / 2
        self.origin_y_m = -(self.height * config.resolution_m) / 2
        self._evidence = [0] * (self.width * self.height)
        self._observed = [False] * (self.width * self.height)

    def insert(self, scan: LaserScan, pose: MappingPose) -> int:
        sensor_origin = self._sensor_origin_in_odom(pose)
        origin_cell = self._world_to_cell(*sensor_origin)
        if origin_cell is None:
            return 0
        inserted = 0
        for index, distance in enumerate(scan.ranges_m):
            if (
                not math.isfinite(distance)
                or distance < scan.range_min_m
                or distance > scan.range_max_m
            ):
                continue
            endpoint = self._endpoint_in_odom(scan, pose, index, distance)
            endpoint_cell = self._world_to_cell(*endpoint)
            if endpoint_cell is None:
                continue
            cells = self._bresenham(origin_cell, endpoint_cell)
            for cell in cells[:-1]:
                self._add_evidence(cell, -1)
            self._add_evidence(cells[-1], 3)
            inserted += 1
        return inserted

    def clear(self) -> None:
        """Forget all accumulated evidence without changing map geometry."""

        self._evidence = [0] * (self.width * self.height)
        self._observed = [False] * (self.width * self.height)

    def message(self, *, header: MessageHeader) -> OccupancyGrid:
        data = []
        for observed, evidence in zip(self._observed, self._evidence):
            if not observed:
                data.append(-1)
            elif evidence >= 2:
                data.append(100)
            elif evidence <= -1:
                data.append(0)
            else:
                data.append(50)
        return OccupancyGrid(
            header=header,
            width=self.width,
            height=self.height,
            resolution_m=self.config.resolution_m,
            origin_x_m=self.origin_x_m,
            origin_y_m=self.origin_y_m,
            data=tuple(data),
        )

    def _sensor_origin_in_odom(self, pose: MappingPose) -> Tuple[float, float]:
        transform = self.config.sensor_transform
        cos_pose = math.cos(pose.yaw_rad)
        sin_pose = math.sin(pose.yaw_rad)
        return (
            pose.x_m + cos_pose * transform.x_m - sin_pose * transform.y_m,
            pose.y_m + sin_pose * transform.x_m + cos_pose * transform.y_m,
        )

    def _endpoint_in_odom(
        self,
        scan: LaserScan,
        pose: MappingPose,
        index: int,
        distance: float,
    ) -> Tuple[float, float]:
        transform = self.config.sensor_transform
        sensor_angle = scan.angle_min_rad + index * scan.angle_increment_rad
        sensor_x = distance * math.cos(sensor_angle)
        sensor_y = distance * math.sin(sensor_angle)
        cos_sensor = math.cos(transform.yaw_rad)
        sin_sensor = math.sin(transform.yaw_rad)
        base_x = transform.x_m + cos_sensor * sensor_x - sin_sensor * sensor_y
        base_y = transform.y_m + sin_sensor * sensor_x + cos_sensor * sensor_y
        cos_pose = math.cos(pose.yaw_rad)
        sin_pose = math.sin(pose.yaw_rad)
        return (
            pose.x_m + cos_pose * base_x - sin_pose * base_y,
            pose.y_m + sin_pose * base_x + cos_pose * base_y,
        )

    def _world_to_cell(self, x_m: float, y_m: float) -> Optional[Tuple[int, int]]:
        x = math.floor((x_m - self.origin_x_m) / self.config.resolution_m)
        y = math.floor((y_m - self.origin_y_m) / self.config.resolution_m)
        if not 0 <= x < self.width or not 0 <= y < self.height:
            return None
        return x, y

    def _add_evidence(self, cell: Tuple[int, int], delta: int) -> None:
        index = cell[1] * self.width + cell[0]
        self._observed[index] = True
        self._evidence[index] = max(-10, min(10, self._evidence[index] + delta))

    @staticmethod
    def _bresenham(
        start: Tuple[int, int], end: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        x0, y0 = start
        x1, y1 = end
        cells = []
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        error = dx + dy
        while True:
            cells.append((x0, y0))
            if x0 == x1 and y0 == y1:
                return cells
            twice_error = 2 * error
            if twice_error >= dy:
                error += dy
                x0 += sx
            if twice_error <= dx:
                error += dx
                y0 += sy


class LocalMappingService:
    """Synchronize scans with fused localization or raw odometry."""

    def __init__(
        self,
        bus: TopicBus,
        grid: LocalOccupancyGrid,
        *,
        max_odometry_age_seconds: float,
        prefer_localization: bool = False,
    ) -> None:
        if max_odometry_age_seconds <= 0:
            raise ValueError("max_odometry_age_seconds must be positive")
        self._bus = bus
        self._grid = grid
        self._max_odometry_age_ns = int(max_odometry_age_seconds * 1_000_000_000)
        self._prefer_localization = prefer_localization
        self._odom_subscription: Optional[TopicSubscription[Odometry2D]] = None
        self._localization_subscription: Optional[
            TopicSubscription[LocalizationPose2D]
        ] = None
        self._scan_subscription: Optional[TopicSubscription[LaserScan]] = None
        self._tasks: Tuple[asyncio.Task[None], ...] = ()
        self._odometry_history: Deque[Odometry2D] = deque(maxlen=_POSE_HISTORY_LIMIT)
        self._localization_history: Deque[LocalizationPose2D] = deque(
            maxlen=_POSE_HISTORY_LIMIT
        )
        self._sequence = 0
        self._state = MappingSessionState.IDLE
        self._session_id = 0
        self._scans_received = 0
        self._scans_inserted = 0
        self._returns_inserted = 0
        self._ignored_inactive_scans = 0
        self._rejected_missing_odometry = 0
        self._rejected_stale_odometry = 0
        self._active_pose_source: Optional[MappingPoseSource] = None
        self._scans_inserted_with_odometry = 0
        self._scans_inserted_with_localization = 0
        self._localization_fallbacks = 0
        self._has_map = False

    @property
    def running(self) -> bool:
        return bool(self._tasks) and any(not task.done() for task in self._tasks)

    @property
    def status(self) -> MappingSessionStatus:
        return MappingSessionStatus(
            enabled=True,
            state=self._state,
            session_id=self._session_id,
            map_sequence=self._sequence,
            scans_received=self._scans_received,
            scans_inserted=self._scans_inserted,
            returns_inserted=self._returns_inserted,
            ignored_inactive_scans=self._ignored_inactive_scans,
            rejected_missing_odometry=self._rejected_missing_odometry,
            rejected_stale_odometry=self._rejected_stale_odometry,
            preferred_pose_source=(
                MappingPoseSource.LOCALIZATION
                if self._prefer_localization
                else MappingPoseSource.ODOMETRY
            ),
            active_pose_source=self._active_pose_source,
            scans_inserted_with_odometry=self._scans_inserted_with_odometry,
            scans_inserted_with_localization=(self._scans_inserted_with_localization),
            localization_fallbacks=self._localization_fallbacks,
            has_map=self._has_map,
        )

    def start_session(self) -> MappingSessionStatus:
        """Start a new session or resume the currently paused session."""

        if self._state == MappingSessionState.IDLE:
            self._session_id += 1
            self._reset_session_counters()
        self._state = MappingSessionState.ACTIVE
        return self.status

    def pause_session(self) -> MappingSessionStatus:
        if self._state == MappingSessionState.ACTIVE:
            self._state = MappingSessionState.PAUSED
        return self.status

    def finish_session(self) -> MappingSessionStatus:
        """Stop inserting scans while retaining the completed map."""

        self._state = MappingSessionState.IDLE
        return self.status

    def clear_map(self) -> MappingSessionStatus:
        """Clear cells while preserving the session state and latest odometry."""

        self._grid.clear()
        self._has_map = False
        self._publish_snapshot(timestamp_monotonic_ns=time.monotonic_ns())
        return self.status

    def reset_session(self) -> MappingSessionStatus:
        """Clear the map and return to an unarmed mapping session."""

        self._state = MappingSessionState.IDLE
        self._odometry_history.clear()
        self._localization_history.clear()
        self._grid.clear()
        self._has_map = False
        self._reset_session_counters()
        self._publish_snapshot(timestamp_monotonic_ns=time.monotonic_ns())
        return self.status

    def _reset_session_counters(self) -> None:
        self._scans_received = 0
        self._scans_inserted = 0
        self._returns_inserted = 0
        self._ignored_inactive_scans = 0
        self._rejected_missing_odometry = 0
        self._rejected_stale_odometry = 0
        self._active_pose_source = None
        self._scans_inserted_with_odometry = 0
        self._scans_inserted_with_localization = 0
        self._localization_fallbacks = 0

    def start(self) -> None:
        if self.running:
            return
        self._odom_subscription = self._bus.subscribe(ODOMETRY, max_queue_size=1)
        if self._prefer_localization:
            self._localization_subscription = self._bus.subscribe(
                LOCALIZATION_POSE, max_queue_size=1
            )
        self._scan_subscription = self._bus.subscribe(LIDAR_SCAN, max_queue_size=1)
        tasks = [asyncio.create_task(self._read_odometry(), name="local-map-odometry")]
        if self._localization_subscription is not None:
            tasks.append(
                asyncio.create_task(
                    self._read_localization(), name="local-map-localization"
                )
            )
        tasks.append(asyncio.create_task(self._read_scans(), name="local-map-scans"))
        self._tasks = tuple(tasks)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = ()
        for subscription in (
            self._odom_subscription,
            self._localization_subscription,
            self._scan_subscription,
        ):
            if subscription is not None:
                subscription.close()
        self._odom_subscription = None
        self._localization_subscription = None
        self._scan_subscription = None

    async def reconfigure_from(self, replacement: "LocalMappingService") -> None:
        """Reset the bounded grid while preserving this service identity."""

        was_running = self.running
        await self.stop()
        self._grid = replacement._grid
        self._max_odometry_age_ns = replacement._max_odometry_age_ns
        self._prefer_localization = replacement._prefer_localization
        self._odometry_history.clear()
        self._localization_history.clear()
        self._state = MappingSessionState.IDLE
        self._reset_session_counters()
        self._has_map = False
        self._publish_snapshot(timestamp_monotonic_ns=time.monotonic_ns())
        if was_running:
            self.start()

    async def _read_odometry(self) -> None:
        subscription = self._odom_subscription
        if subscription is None:
            return
        try:
            async for odometry in subscription:
                self._odometry_history.append(odometry)
        except SubscriptionClosed:
            return

    async def _read_localization(self) -> None:
        subscription = self._localization_subscription
        if subscription is None:
            return
        try:
            async for localization in subscription:
                self._localization_history.append(localization)
        except SubscriptionClosed:
            return

    def _fresh_pose_at_scan(
        self, scan: LaserScan, history: Deque[MappingPoseT]
    ) -> Optional[MappingPoseT]:
        scan_timestamp_ns = scan.header.timestamp_monotonic_ns
        for pose in reversed(history):
            age_ns = scan_timestamp_ns - pose.header.timestamp_monotonic_ns
            if age_ns < 0:
                continue
            return pose if age_ns <= self._max_odometry_age_ns else None
        return None

    def _select_pose(
        self, scan: LaserScan
    ) -> Tuple[Optional[MappingPose], Optional[MappingPoseSource]]:
        localization = self._fresh_pose_at_scan(scan, self._localization_history)
        if self._prefer_localization and localization is not None:
            return localization, MappingPoseSource.LOCALIZATION

        odometry = self._fresh_pose_at_scan(scan, self._odometry_history)
        if odometry is not None:
            if self._prefer_localization:
                self._localization_fallbacks += 1
            return odometry, MappingPoseSource.ODOMETRY
        return None, None

    async def _read_scans(self) -> None:
        subscription = self._scan_subscription
        if subscription is None:
            return
        try:
            async for scan in subscription:
                self._scans_received += 1
                if self._state != MappingSessionState.ACTIVE:
                    self._ignored_inactive_scans += 1
                    continue
                pose, source = self._select_pose(scan)
                if pose is None or source is None:
                    all_histories_empty = not self._odometry_history and (
                        not self._prefer_localization or not self._localization_history
                    )
                    if all_histories_empty:
                        self._rejected_missing_odometry += 1
                    else:
                        self._rejected_stale_odometry += 1
                    continue
                inserted = self._grid.insert(scan, pose)
                self._active_pose_source = source
                if source == MappingPoseSource.LOCALIZATION:
                    self._scans_inserted_with_localization += 1
                else:
                    self._scans_inserted_with_odometry += 1
                self._scans_inserted += 1
                self._returns_inserted += inserted
                self._has_map = self._has_map or inserted > 0
                self._publish_snapshot(
                    timestamp_monotonic_ns=scan.header.timestamp_monotonic_ns,
                    source_timestamp_ns=scan.header.source_timestamp_ns,
                )
        except SubscriptionClosed:
            return

    def _publish_snapshot(
        self,
        *,
        timestamp_monotonic_ns: int,
        source_timestamp_ns: Optional[int] = None,
    ) -> None:
        self._sequence += 1
        self._bus.publish(
            LOCAL_MAP,
            self._grid.message(
                header=MessageHeader(
                    sequence=self._sequence,
                    frame_id="odom",
                    timestamp_monotonic_ns=timestamp_monotonic_ns,
                    source_timestamp_ns=source_timestamp_ns,
                )
            ),
        )


__all__ = [
    "LocalMappingService",
    "LocalOccupancyGrid",
    "LocalOccupancyGridConfig",
    "StaticTransform2D",
]
