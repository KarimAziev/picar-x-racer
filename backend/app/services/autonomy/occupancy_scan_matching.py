"""LiDAR localization against frozen observed occupancy, independent of simulation."""

import asyncio
from dataclasses import replace
import heapq
import math
from typing import Optional

from app.schemas.autonomy import (
    LaserScan,
    LocalizationPose2D,
    OccupancyGrid,
    MappingSessionStatus,
    MappingSessionState,
)
from app.schemas.robot.pose_estimation import OccupancyMapScanMatchingConfig
from app.services.autonomy.scan_matching import (
    KnownWorldScanMatcherConfig,
    KnownWorldScanMatcherService,
    PlanarScanMatcher,
    ScanMatchResult,
    ScanMatchRejection,
)
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import LOCAL_MAP, MAPPING_SESSION


class OccupancyDistanceField:
    """Bounded eight-neighbor distance field, sampled in the grid's rotated frame."""

    def __init__(
        self,
        grid: OccupancyGrid,
        *,
        threshold: int,
        cap_m: float,
        min_occupied_cells: int,
    ) -> None:
        if grid.width * grid.height > 1_000_000:
            raise ValueError("occupancy reference exceeds one million cells")
        self.grid = grid
        self.cap_m = cap_m
        self._cos = math.cos(grid.origin_yaw_rad)
        self._sin = math.sin(grid.origin_yaw_rad)
        occupied = [
            index for index, value in enumerate(grid.data) if value >= threshold
        ]
        if len(occupied) < min_occupied_cells:
            raise ValueError("map contains too few occupied cells for localization")
        distances = [cap_m] * len(grid.data)
        queue = [(0.0, index) for index in occupied]
        for index in occupied:
            distances[index] = 0.0
        heapq.heapify(queue)
        neighbors = [
            (dx, dy, math.hypot(dx, dy) * grid.resolution_m)
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            if dx or dy
        ]
        while queue:
            distance, index = heapq.heappop(queue)
            if distance > distances[index]:
                continue
            x, y = index % grid.width, index // grid.width
            for dx, dy, cost in neighbors:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < grid.width and 0 <= ny < grid.height):
                    continue
                neighbor = ny * grid.width + nx
                candidate = distance + cost
                if candidate < distances[neighbor]:
                    distances[neighbor] = candidate
                    heapq.heappush(queue, (candidate, neighbor))
        self._distances = distances

    def _grid_point(self, x_m: float, y_m: float) -> tuple[float, float]:
        dx, dy = x_m - self.grid.origin_x_m, y_m - self.grid.origin_y_m
        return (
            (self._cos * dx + self._sin * dy) / self.grid.resolution_m,
            (-self._sin * dx + self._cos * dy) / self.grid.resolution_m,
        )

    def known(self, x_m: float, y_m: float) -> bool:
        x, y = self._grid_point(x_m, y_m)
        return (
            0 <= x < self.grid.width
            and 0 <= y < self.grid.height
            and self.grid.data[int(y) * self.grid.width + int(x)] >= 0
        )

    def distance_to_nearest(self, x_m: float, y_m: float) -> float:
        if not self.known(x_m, y_m):
            return self.cap_m
        x, y = self._grid_point(x_m, y_m)
        # Cell-center interpolation avoids a flat objective inside every cell.
        x -= 0.5
        y -= 0.5
        ix, iy = math.floor(x), math.floor(y)
        fx, fy = x - ix, y - iy
        value = 0.0
        for dx, wx in ((0, 1 - fx), (1, fx)):
            for dy, wy in ((0, 1 - fy), (1, fy)):
                nx, ny = ix + dx, iy + dy
                distance = (
                    self._distances[ny * self.grid.width + nx]
                    if 0 <= nx < self.grid.width and 0 <= ny < self.grid.height
                    else self.cap_m
                )
                value += wx * wy * distance
        return value

    def free(self, x_m: float, y_m: float) -> bool:
        if not self.known(x_m, y_m):
            return False
        x, y = self._grid_point(x_m, y_m)
        return self.grid.data[int(y) * self.grid.width + int(x)] < 50


class OccupancyMapScanMatcher(PlanarScanMatcher):
    def __init__(
        self,
        grid: OccupancyGrid,
        config: KnownWorldScanMatcherConfig,
        settings: OccupancyMapScanMatchingConfig,
    ) -> None:
        self.grid = grid
        self.settings = settings
        self.field = OccupancyDistanceField(
            grid,
            threshold=settings.occupied_threshold,
            cap_m=config.max_residual_m,
            min_occupied_cells=settings.min_occupied_cells,
        )
        # A discretized map cannot justify finer position precision than its cells.
        config = replace(
            config,
            odom_origin_in_world=(0, 0, 0),
            source="occupancy_map_scan_matcher",
            position_stddev_m=max(config.position_stddev_m, grid.resolution_m),
        )
        super().__init__(self.field, config)

    def match(
        self, scan: LaserScan, prior: LocalizationPose2D, *, sequence: int
    ) -> ScanMatchResult:
        if prior.header.frame_id != self.grid.header.frame_id:
            raise ValueError("localization and occupancy map frames do not match")
        result = super().match(scan, prior, sequence=sequence)
        observation = result.observation
        if observation is None:
            return result
        points = self._sample_base_points(scan)
        best = (observation.x_m, observation.y_m, observation.yaw_rad)
        rejection: Optional[ScanMatchRejection] = None
        c, s = math.cos(best[2]), math.sin(best[2])
        overlap = sum(
            self.field.known(best[0] + c * x - s * y, best[1] + s * x + c * y)
            for x, y in points
        ) / len(points)
        if (
            not self.field.free(best[0], best[1])
            or overlap < self.settings.min_overlap_fraction
        ):
            rejection = "insufficient_overlap"
        elif (
            abs(best[0] - prior.x_m) >= self.config.search_translation_m
            or abs(best[1] - prior.y_m) >= self.config.search_translation_m
            or abs(self._normalize_angle(best[2] - prior.yaw_rad))
            >= self.config.search_heading_rad
        ):
            rejection = "search_boundary"
        else:
            distance = max(
                self.settings.ambiguity_distance_m, 2 * self.grid.resolution_m
            )
            probes = [
                (
                    best[0] + distance * math.cos(angle * math.pi / 4),
                    best[1] + distance * math.sin(angle * math.pi / 4),
                    best[2],
                )
                for angle in range(8)
            ]
            angle = math.radians(self.settings.ambiguity_heading_deg)
            probes += [(best[0], best[1], best[2] + delta) for delta in (-angle, angle)]
            if any(
                self._score(probe, points)
                <= (result.mean_error_m or 0) + self.settings.ambiguity_margin_m
                for probe in probes
            ):
                rejection = "ambiguous_alignment"
        return (
            replace(result, observation=None, rejection=rejection)
            if rejection
            else result
        )


class OccupancyMapScanMatcherService(KnownWorldScanMatcherService):
    """Select a frozen map on the event loop; discard work across map transitions."""

    def __init__(
        self,
        bus: TopicBus,
        config: KnownWorldScanMatcherConfig,
        settings: OccupancyMapScanMatchingConfig,
    ) -> None:
        self._config = config
        self._settings = settings
        super().__init__(
            bus, None, max_pose_age_seconds=settings.max_pose_age_ms / 1000
        )

    def reset(self) -> None:
        super().reset()
        self.reference = "occupancy_map"
        self._reference_grid: Optional[OccupancyGrid] = None
        self._reference_session: Optional[MappingSessionStatus] = None
        self.matcher = None

    def _reference_is_current(self) -> bool:
        return (
            self._reference_grid is not None
            and self._bus.latest(LOCAL_MAP) is self._reference_grid
            and self._bus.latest(MAPPING_SESSION) is self._reference_session
        )

    async def _prepare_reference(self, scan: LaserScan) -> bool:
        grid = self._bus.latest(LOCAL_MAP)
        session = self._bus.latest(MAPPING_SESSION)
        if (
            grid is None
            or session is None
            or not session.enabled
            or not session.has_map
            or session.state == MappingSessionState.ACTIVE
            or session.map_sequence != grid.header.sequence
        ):
            self.reference_map_sequence = None
            self.latest_observation = None
            self.last_rejection = (
                "pause or finish mapping with an observed map to enable localization"
            )
            return False
        if scan.header.timestamp_monotonic_ns <= grid.header.timestamp_monotonic_ns:
            self.last_rejection = "scan predates the frozen map snapshot"
            return False
        self._reference_session = session
        if grid is not self._reference_grid:
            self._reference_grid = grid
            self.reference_map_sequence = None
            self.latest_observation = None
            self.matcher = None
            try:
                matcher = await asyncio.to_thread(
                    OccupancyMapScanMatcher, grid, self._config, self._settings
                )
            except ValueError as error:
                self.last_rejection = str(error)
                return False
            if not self._reference_is_current():
                self.last_rejection = "map changed while preparing localization"
                self._reference_grid = None
                return False
            self.matcher = matcher
        if self.matcher is None:
            return False
        self.reference_map_sequence = grid.header.sequence
        return True
