"""Fixed local occupancy grid built from LiDAR scans and Ackermann odometry."""

import asyncio
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.schemas.autonomy import LaserScan, MessageHeader, OccupancyGrid, Odometry2D
from app.services.autonomy.topic_bus import (
    SubscriptionClosed,
    TopicBus,
    TopicSubscription,
)
from app.services.autonomy.topics import LIDAR_SCAN, LOCAL_MAP, ODOMETRY


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

    def insert(self, scan: LaserScan, pose: Odometry2D) -> int:
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

    def _sensor_origin_in_odom(self, pose: Odometry2D) -> Tuple[float, float]:
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
        pose: Odometry2D,
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
    """Synchronize latest odometry with scans and publish map snapshots."""

    def __init__(
        self,
        bus: TopicBus,
        grid: LocalOccupancyGrid,
        *,
        max_odometry_age_seconds: float,
    ) -> None:
        if max_odometry_age_seconds <= 0:
            raise ValueError("max_odometry_age_seconds must be positive")
        self._bus = bus
        self._grid = grid
        self._max_odometry_age_ns = int(max_odometry_age_seconds * 1_000_000_000)
        self._odom_subscription: Optional[TopicSubscription[Odometry2D]] = None
        self._scan_subscription: Optional[TopicSubscription[LaserScan]] = None
        self._tasks: Tuple[asyncio.Task[None], ...] = ()
        self._latest_odometry: Optional[Odometry2D] = None
        self._sequence = 0

    @property
    def running(self) -> bool:
        return bool(self._tasks) and any(not task.done() for task in self._tasks)

    def start(self) -> None:
        if self.running:
            return
        self._odom_subscription = self._bus.subscribe(ODOMETRY, max_queue_size=1)
        self._scan_subscription = self._bus.subscribe(LIDAR_SCAN, max_queue_size=1)
        self._tasks = (
            asyncio.create_task(self._read_odometry(), name="local-map-odometry"),
            asyncio.create_task(self._read_scans(), name="local-map-scans"),
        )

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = ()
        for subscription in (self._odom_subscription, self._scan_subscription):
            if subscription is not None:
                subscription.close()
        self._odom_subscription = None
        self._scan_subscription = None

    async def reconfigure_from(self, replacement: "LocalMappingService") -> None:
        """Reset the bounded grid while preserving this service identity."""

        was_running = self.running
        await self.stop()
        self._grid = replacement._grid
        self._max_odometry_age_ns = replacement._max_odometry_age_ns
        self._latest_odometry = None
        self._sequence = 0
        if was_running:
            self.start()

    async def _read_odometry(self) -> None:
        subscription = self._odom_subscription
        if subscription is None:
            return
        try:
            async for odometry in subscription:
                self._latest_odometry = odometry
        except SubscriptionClosed:
            return

    async def _read_scans(self) -> None:
        subscription = self._scan_subscription
        if subscription is None:
            return
        try:
            async for scan in subscription:
                odometry = self._latest_odometry
                if odometry is None:
                    continue
                age_ns = abs(
                    scan.header.timestamp_monotonic_ns
                    - odometry.header.timestamp_monotonic_ns
                )
                if age_ns > self._max_odometry_age_ns:
                    continue
                self._grid.insert(scan, odometry)
                self._sequence += 1
                self._bus.publish(
                    LOCAL_MAP,
                    self._grid.message(
                        header=MessageHeader(
                            sequence=self._sequence,
                            frame_id="odom",
                            timestamp_monotonic_ns=scan.header.timestamp_monotonic_ns,
                            source_timestamp_ns=scan.header.source_timestamp_ns,
                        )
                    ),
                )
        except SubscriptionClosed:
            return


__all__ = [
    "LocalMappingService",
    "LocalOccupancyGrid",
    "LocalOccupancyGridConfig",
    "StaticTransform2D",
]
