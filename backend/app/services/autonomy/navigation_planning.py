"""Collision-aware A* route previews over the native occupancy grid."""

import asyncio
import heapq
import math
import time
from dataclasses import dataclass
from itertools import count
from typing import Dict, Iterable, List, Literal, Optional, Sequence, Tuple

from app.schemas.autonomy import (
    NavigationDirection,
    NavigationGoalRequest,
    NavigationPlanState,
    NavigationPlanStatus,
    NavigationPoint,
    OccupancyGrid,
)
from app.services.autonomy.hybrid_astar import (
    HybridAStarPlanner,
    HybridPathNotFound,
    HybridPose,
)
from app.services.autonomy.path_smoothing import (
    AckermannPathSmoother,
    PathGeometryRejected,
)
from app.services.autonomy.topic_bus import TopicBus
from app.services.autonomy.topics import LOCALIZATION_POSE, LOCAL_MAP, ODOMETRY


GridCell = Tuple[int, int]
PlanningPose = Tuple[float, float, float, Literal["localization", "odometry"]]
_SQRT_TWO = math.sqrt(2.0)


class NavigationPlanRejected(ValueError):
    """The requested goal cannot be planned safely on the supplied map."""


@dataclass(frozen=True)
class GridPlan:
    path: Tuple[NavigationPoint, ...]
    path_directions: Tuple[NavigationDirection, ...]
    path_length_m: float
    reverse_distance_m: float
    gear_changes: int
    expanded_nodes: int
    geometry_validated: bool = False
    smoothed: bool = False
    raw_waypoint_count: int = 0
    max_curvature_per_m: Optional[float] = None
    curvature_limit_per_m: Optional[float] = None
    minimum_turning_radius_m: Optional[float] = None
    initial_heading_error_rad: Optional[float] = None
    planning_method: Literal["grid_astar", "hybrid_astar"] = "grid_astar"


class OccupancyGridPlanner:
    """Plan a simplified 8-connected route without diagonal corner cutting."""

    def __init__(
        self,
        *,
        occupied_threshold: int = 65,
        max_cells: int = 1_000_000,
        path_smoother: Optional[AckermannPathSmoother] = None,
    ) -> None:
        if not 0 <= occupied_threshold <= 100:
            raise ValueError("occupied threshold must be between 0 and 100")
        if max_cells <= 0:
            raise ValueError("maximum cell count must be positive")
        self.occupied_threshold = occupied_threshold
        self.max_cells = max_cells
        self.path_smoother = path_smoother
        self.hybrid_planner = (
            HybridAStarPlanner(
                curvature_limit_per_m=path_smoother.curvature_limit_per_m
            )
            if path_smoother is not None
            else None
        )

    def plan(
        self,
        grid: OccupancyGrid,
        *,
        start_x_m: float,
        start_y_m: float,
        start_yaw_rad: Optional[float] = None,
        goal: NavigationGoalRequest,
    ) -> GridPlan:
        if grid.width * grid.height > self.max_cells:
            raise NavigationPlanRejected(
                "occupancy map is too large for interactive route planning"
            )
        start_cell = self._world_to_cell(grid, start_x_m, start_y_m)
        if start_cell is None:
            raise NavigationPlanRejected("current pose is outside the occupancy map")
        goal_cell = self._world_to_cell(grid, goal.x_m, goal.y_m)
        if goal_cell is None:
            raise NavigationPlanRejected("selected goal is outside the occupancy map")

        goal_value = self._value(grid, goal_cell)
        if goal_value < 0 and not goal.allow_unknown:
            raise NavigationPlanRejected("selected goal lies in unknown map space")
        if goal_value >= self.occupied_threshold:
            raise NavigationPlanRejected("selected goal lies in an occupied cell")

        blocked = self._inflated_obstacles(
            grid,
            clearance_m=goal.clearance_m,
            allow_unknown=goal.allow_unknown,
        )
        if self._is_blocked(grid, blocked, start_cell):
            raise NavigationPlanRejected(
                "current pose does not have the requested obstacle clearance"
            )
        if self._is_blocked(grid, blocked, goal_cell):
            raise NavigationPlanRejected(
                "selected goal does not have the requested obstacle clearance"
            )

        cell_path, expanded_nodes = self._a_star(
            grid,
            blocked,
            start_cell,
            goal_cell,
        )
        if cell_path is None:
            raise NavigationPlanRejected(
                "no collision-free route reaches the selected goal"
            )
        simplified = self._simplify_path(grid, blocked, cell_path)
        raw_path = self._metric_path(
            grid,
            simplified,
            start=NavigationPoint(x_m=start_x_m, y_m=start_y_m),
            goal=NavigationPoint(x_m=goal.x_m, y_m=goal.y_m),
        )
        path = raw_path
        path_directions = (NavigationDirection.FORWARD,) * (len(path) - 1)
        geometry_validated = False
        smoothed = False
        max_curvature_per_m = None
        curvature_limit_per_m = None
        minimum_turning_radius_m = None
        initial_heading_error_rad = None
        planning_method: Literal["grid_astar", "hybrid_astar"] = "grid_astar"
        if self.path_smoother is not None:
            if start_yaw_rad is None:
                raise NavigationPlanRejected(
                    "current pose heading is required for curvature validation"
                )
            clearance_check = lambda candidate: self._metric_path_is_clear(
                grid, blocked, candidate
            )
            try:
                geometry = self.path_smoother.smooth(
                    raw_path,
                    start_yaw_rad=start_yaw_rad,
                    is_clear=clearance_check,
                )
            except PathGeometryRejected as smoothing_error:
                if self.hybrid_planner is None:
                    raise NavigationPlanRejected(
                        str(smoothing_error)
                    ) from smoothing_error
                try:
                    recovery = self.hybrid_planner.plan(
                        start=HybridPose(
                            x_m=start_x_m,
                            y_m=start_y_m,
                            yaw_rad=start_yaw_rad,
                        ),
                        goal=NavigationPoint(x_m=goal.x_m, y_m=goal.y_m),
                        grid_resolution_m=grid.resolution_m,
                        is_clear=clearance_check,
                        guide_path=raw_path,
                    )
                except HybridPathNotFound as recovery_error:
                    raise NavigationPlanRejected(
                        "the grid route is not drivable and curvature-aware "
                        f"recovery failed: {recovery_error}"
                    ) from recovery_error
                expanded_nodes += recovery.expanded_nodes
                planning_method = "hybrid_astar"
                path = recovery.path
                path_directions = recovery.path_directions
                geometry_validated = True
                smoothed = False
                max_curvature_per_m = recovery.max_curvature_per_m
                curvature_limit_per_m = self.path_smoother.curvature_limit_per_m
                minimum_turning_radius_m = self.path_smoother.minimum_turning_radius_m
                initial_heading_error_rad = self._initial_heading_error(
                    path,
                    path_directions,
                    start_yaw_rad,
                )
            else:
                path = geometry.path
                path_directions = (NavigationDirection.FORWARD,) * (len(path) - 1)
                geometry_validated = True
                smoothed = geometry.smoothed
                max_curvature_per_m = geometry.max_curvature_per_m
                curvature_limit_per_m = geometry.curvature_limit_per_m
                minimum_turning_radius_m = geometry.minimum_turning_radius_m
                initial_heading_error_rad = geometry.initial_heading_error_rad
        segment_lengths = tuple(
            math.hypot(end.x_m - start.x_m, end.y_m - start.y_m)
            for start, end in zip(path, path[1:])
        )
        return GridPlan(
            path=path,
            path_directions=path_directions,
            path_length_m=sum(segment_lengths),
            reverse_distance_m=sum(
                length
                for length, direction in zip(segment_lengths, path_directions)
                if direction == NavigationDirection.REVERSE
            ),
            gear_changes=sum(
                before != after
                for before, after in zip(path_directions, path_directions[1:])
            ),
            expanded_nodes=expanded_nodes,
            geometry_validated=geometry_validated,
            smoothed=smoothed,
            raw_waypoint_count=len(raw_path),
            max_curvature_per_m=max_curvature_per_m,
            curvature_limit_per_m=curvature_limit_per_m,
            minimum_turning_radius_m=minimum_turning_radius_m,
            initial_heading_error_rad=initial_heading_error_rad,
            planning_method=planning_method,
        )

    @staticmethod
    def _initial_heading_error(
        path: Sequence[NavigationPoint],
        directions: Sequence[NavigationDirection],
        start_yaw_rad: float,
    ) -> float:
        if len(path) < 2 or not directions:
            return 0.0
        travel_heading = math.atan2(
            path[1].y_m - path[0].y_m,
            path[1].x_m - path[0].x_m,
        )
        vehicle_heading = travel_heading + (
            math.pi if directions[0] == NavigationDirection.REVERSE else 0.0
        )
        return (vehicle_heading - start_yaw_rad + math.pi) % (2 * math.pi) - math.pi

    def _metric_path_is_clear(
        self,
        grid: OccupancyGrid,
        blocked: bytearray,
        path: Sequence[NavigationPoint],
    ) -> bool:
        """Sample world-space segments densely against the inflated grid."""

        if len(path) < 2:
            return False
        sample_spacing_m = grid.resolution_m * 0.25
        for start, end in zip(path, path[1:]):
            distance_m = math.hypot(end.x_m - start.x_m, end.y_m - start.y_m)
            if distance_m <= 1e-9:
                return False
            sample_count = max(1, math.ceil(distance_m / sample_spacing_m))
            for sample_index in range(sample_count + 1):
                fraction = sample_index / sample_count
                cell = self._world_to_cell(
                    grid,
                    start.x_m + fraction * (end.x_m - start.x_m),
                    start.y_m + fraction * (end.y_m - start.y_m),
                )
                if cell is None or self._is_blocked(grid, blocked, cell):
                    return False
        return True

    def _inflated_obstacles(
        self,
        grid: OccupancyGrid,
        *,
        clearance_m: float,
        allow_unknown: bool,
    ) -> bytearray:
        blocked = bytearray(grid.width * grid.height)
        obstacle_cells = []
        for index, value in enumerate(grid.data):
            if value >= self.occupied_threshold or (value < 0 and not allow_unknown):
                obstacle_cells.append((index % grid.width, index // grid.width))

        radius_cells = math.ceil(clearance_m / grid.resolution_m)
        if radius_cells == 0:
            for cell_x, cell_y in obstacle_cells:
                blocked[cell_y * grid.width + cell_x] = 1
            return blocked

        # The map boundary is unknown space too. Keep the planned vehicle
        # center far enough inside the grid that its requested clearance does
        # not extend beyond the map snapshot.
        for cell_y in range(grid.height):
            for cell_x in range(grid.width):
                distance_to_boundary_m = (
                    min(
                        cell_x + 0.5,
                        cell_y + 0.5,
                        grid.width - cell_x - 0.5,
                        grid.height - cell_y - 0.5,
                    )
                    * grid.resolution_m
                )
                if distance_to_boundary_m < clearance_m:
                    blocked[cell_y * grid.width + cell_x] = 1

        radius_squared = (clearance_m / grid.resolution_m) ** 2
        offsets = tuple(
            (offset_x, offset_y)
            for offset_y in range(-radius_cells, radius_cells + 1)
            for offset_x in range(-radius_cells, radius_cells + 1)
            if offset_x * offset_x + offset_y * offset_y <= radius_squared
        )
        for obstacle_x, obstacle_y in obstacle_cells:
            for offset_x, offset_y in offsets:
                cell_x = obstacle_x + offset_x
                cell_y = obstacle_y + offset_y
                if 0 <= cell_x < grid.width and 0 <= cell_y < grid.height:
                    blocked[cell_y * grid.width + cell_x] = 1
        return blocked

    def _a_star(
        self,
        grid: OccupancyGrid,
        blocked: bytearray,
        start: GridCell,
        goal: GridCell,
    ) -> Tuple[Optional[Tuple[GridCell, ...]], int]:
        if start == goal:
            return (start,), 0

        frontier: List[Tuple[float, float, int, GridCell]] = []
        order = count()
        initial_heuristic = self._octile_distance(start, goal)
        heapq.heappush(
            frontier,
            (initial_heuristic, initial_heuristic, next(order), start),
        )
        came_from: Dict[GridCell, GridCell] = {}
        cost_to: Dict[GridCell, float] = {start: 0.0}
        expanded = 0

        while frontier:
            _, _, _, current = heapq.heappop(frontier)
            if current == goal:
                return self._reconstruct(came_from, current), expanded
            expanded += 1
            current_cost = cost_to[current]
            for neighbor, movement_cost in self._neighbors(grid, blocked, current):
                candidate_cost = current_cost + movement_cost
                if candidate_cost >= cost_to.get(neighbor, math.inf):
                    continue
                cost_to[neighbor] = candidate_cost
                came_from[neighbor] = current
                heuristic = self._octile_distance(neighbor, goal)
                heapq.heappush(
                    frontier,
                    (
                        candidate_cost + heuristic,
                        heuristic,
                        next(order),
                        neighbor,
                    ),
                )
        return None, expanded

    def _neighbors(
        self,
        grid: OccupancyGrid,
        blocked: bytearray,
        cell: GridCell,
    ) -> Iterable[Tuple[GridCell, float]]:
        cell_x, cell_y = cell
        for offset_x, offset_y in (
            (1, 0),
            (0, 1),
            (-1, 0),
            (0, -1),
            (1, 1),
            (-1, 1),
            (-1, -1),
            (1, -1),
        ):
            neighbor = (cell_x + offset_x, cell_y + offset_y)
            if not self._in_bounds(grid, neighbor) or self._is_blocked(
                grid, blocked, neighbor
            ):
                continue
            diagonal = offset_x != 0 and offset_y != 0
            if diagonal and (
                self._is_blocked(grid, blocked, (cell_x + offset_x, cell_y))
                or self._is_blocked(grid, blocked, (cell_x, cell_y + offset_y))
            ):
                continue
            yield neighbor, _SQRT_TWO if diagonal else 1.0

    def _simplify_path(
        self,
        grid: OccupancyGrid,
        blocked: bytearray,
        path: Sequence[GridCell],
    ) -> Tuple[GridCell, ...]:
        if len(path) <= 2:
            return tuple(path)
        simplified = [path[0]]
        anchor_index = 0
        while anchor_index < len(path) - 1:
            visible_index = len(path) - 1
            while visible_index > anchor_index + 1 and not self._line_is_clear(
                grid,
                blocked,
                path[anchor_index],
                path[visible_index],
            ):
                visible_index -= 1
            simplified.append(path[visible_index])
            anchor_index = visible_index
        return tuple(simplified)

    def _line_is_clear(
        self,
        grid: OccupancyGrid,
        blocked: bytearray,
        start: GridCell,
        end: GridCell,
    ) -> bool:
        previous = start
        for cell in self._line_cells(start, end):
            if self._is_blocked(grid, blocked, cell):
                return False
            if cell[0] != previous[0] and cell[1] != previous[1]:
                if self._is_blocked(grid, blocked, (cell[0], previous[1])) or (
                    self._is_blocked(grid, blocked, (previous[0], cell[1]))
                ):
                    return False
            previous = cell
        return True

    @staticmethod
    def _line_cells(start: GridCell, end: GridCell) -> Iterable[GridCell]:
        x, y = start
        end_x, end_y = end
        delta_x = abs(end_x - x)
        step_x = 1 if x < end_x else -1
        delta_y = -abs(end_y - y)
        step_y = 1 if y < end_y else -1
        error = delta_x + delta_y
        while True:
            yield x, y
            if x == end_x and y == end_y:
                return
            twice_error = 2 * error
            if twice_error >= delta_y:
                error += delta_y
                x += step_x
            if twice_error <= delta_x:
                error += delta_x
                y += step_y

    def _metric_path(
        self,
        grid: OccupancyGrid,
        cells: Sequence[GridCell],
        *,
        start: NavigationPoint,
        goal: NavigationPoint,
    ) -> Tuple[NavigationPoint, ...]:
        if not cells:
            return ()
        points = [start]
        points.extend(self._cell_center(grid, cell) for cell in cells[1:-1])
        if math.hypot(goal.x_m - points[-1].x_m, goal.y_m - points[-1].y_m) > 1e-9:
            points.append(goal)
        return tuple(points)

    def _world_to_cell(
        self, grid: OccupancyGrid, x_m: float, y_m: float
    ) -> Optional[GridCell]:
        delta_x = x_m - grid.origin_x_m
        delta_y = y_m - grid.origin_y_m
        cosine = math.cos(grid.origin_yaw_rad)
        sine = math.sin(grid.origin_yaw_rad)
        cell = (
            math.floor((cosine * delta_x + sine * delta_y) / grid.resolution_m),
            math.floor((-sine * delta_x + cosine * delta_y) / grid.resolution_m),
        )
        return cell if self._in_bounds(grid, cell) else None

    @staticmethod
    def _cell_center(grid: OccupancyGrid, cell: GridCell) -> NavigationPoint:
        local_x = (cell[0] + 0.5) * grid.resolution_m
        local_y = (cell[1] + 0.5) * grid.resolution_m
        cosine = math.cos(grid.origin_yaw_rad)
        sine = math.sin(grid.origin_yaw_rad)
        return NavigationPoint(
            x_m=grid.origin_x_m + cosine * local_x - sine * local_y,
            y_m=grid.origin_y_m + sine * local_x + cosine * local_y,
        )

    @staticmethod
    def _octile_distance(start: GridCell, goal: GridCell) -> float:
        delta_x = abs(goal[0] - start[0])
        delta_y = abs(goal[1] - start[1])
        return max(delta_x, delta_y) + (_SQRT_TWO - 1.0) * min(delta_x, delta_y)

    @staticmethod
    def _reconstruct(
        came_from: Dict[GridCell, GridCell], current: GridCell
    ) -> Tuple[GridCell, ...]:
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return tuple(path)

    @staticmethod
    def _in_bounds(grid: OccupancyGrid, cell: GridCell) -> bool:
        return 0 <= cell[0] < grid.width and 0 <= cell[1] < grid.height

    @staticmethod
    def _is_blocked(grid: OccupancyGrid, blocked: bytearray, cell: GridCell) -> bool:
        if not OccupancyGridPlanner._in_bounds(grid, cell):
            return True
        return bool(blocked[cell[1] * grid.width + cell[0]])

    @staticmethod
    def _value(grid: OccupancyGrid, cell: GridCell) -> int:
        return grid.data[cell[1] * grid.width + cell[0]]


class NavigationPlanningService:
    """Hold the latest planning-only route preview for the operator UI."""

    def __init__(
        self,
        bus: TopicBus,
        planner: Optional[OccupancyGridPlanner] = None,
        *,
        localization_timeout_seconds: float = 0.5,
    ) -> None:
        if localization_timeout_seconds <= 0:
            raise ValueError("localization timeout must be positive")
        self._bus = bus
        self._planner = planner or OccupancyGridPlanner()
        self._localization_timeout_ns = int(localization_timeout_seconds * 1e9)
        self._status = NavigationPlanStatus.idle()
        self._lock = asyncio.Lock()

    @property
    def status(self) -> NavigationPlanStatus:
        return self._status

    async def plan(self, request: NavigationGoalRequest) -> NavigationPlanStatus:
        async with self._lock:
            grid = self._bus.latest(LOCAL_MAP)
            goal = NavigationPoint(x_m=request.x_m, y_m=request.y_m)
            if grid is None:
                return self._set_rejected(
                    request,
                    goal=goal,
                    reason="no occupancy map is available",
                    available=False,
                )
            pose = self._planning_pose(grid.header.frame_id)
            if pose is None:
                return self._set_rejected(
                    request,
                    goal=goal,
                    reason="no pose is available in the occupancy-map frame",
                    available=False,
                    map_sequence=grid.header.sequence,
                    frame_id=grid.header.frame_id,
                )
            start_x_m, start_y_m, start_yaw_rad, pose_source = pose
            start = NavigationPoint(x_m=start_x_m, y_m=start_y_m)
            try:
                plan = await asyncio.to_thread(
                    self._planner.plan,
                    grid,
                    start_x_m=start_x_m,
                    start_y_m=start_y_m,
                    start_yaw_rad=start_yaw_rad,
                    goal=request,
                )
            except NavigationPlanRejected as error:
                return self._set_rejected(
                    request,
                    goal=goal,
                    start=start,
                    reason=str(error),
                    map_sequence=grid.header.sequence,
                    pose_source=pose_source,
                    start_yaw_rad=start_yaw_rad,
                    frame_id=grid.header.frame_id,
                )
            except Exception as error:
                self._status = NavigationPlanStatus(
                    available=True,
                    state=NavigationPlanState.FAILED,
                    frame_id=grid.header.frame_id,
                    goal=goal,
                    start=start,
                    clearance_m=request.clearance_m,
                    allow_unknown=request.allow_unknown,
                    map_sequence=grid.header.sequence,
                    pose_source=pose_source,
                    start_yaw_rad=start_yaw_rad,
                    reason=f"planner failed: {error}",
                )
                return self._status

            current_grid = self._bus.latest(LOCAL_MAP)
            if (
                current_grid is None
                or current_grid.header.frame_id != grid.header.frame_id
                or current_grid.header.sequence != grid.header.sequence
            ):
                return self._set_rejected(
                    request,
                    goal=goal,
                    start=start,
                    reason=(
                        "the occupancy map changed while the route was being planned; "
                        "pause or finish mapping and try again"
                    ),
                    map_sequence=grid.header.sequence,
                    pose_source=pose_source,
                    start_yaw_rad=start_yaw_rad,
                    frame_id=grid.header.frame_id,
                )

            self._status = NavigationPlanStatus(
                available=True,
                state=NavigationPlanState.READY,
                frame_id=grid.header.frame_id,
                goal=goal,
                start=start,
                path=plan.path,
                path_directions=plan.path_directions,
                path_length_m=plan.path_length_m,
                reverse_distance_m=plan.reverse_distance_m,
                gear_changes=plan.gear_changes,
                clearance_m=request.clearance_m,
                allow_unknown=request.allow_unknown,
                map_sequence=grid.header.sequence,
                pose_source=pose_source,
                start_yaw_rad=start_yaw_rad,
                expanded_nodes=plan.expanded_nodes,
                planning_method=plan.planning_method,
                geometry_validated=plan.geometry_validated,
                smoothed=plan.smoothed,
                raw_waypoint_count=plan.raw_waypoint_count,
                max_curvature_per_m=plan.max_curvature_per_m,
                curvature_limit_per_m=plan.curvature_limit_per_m,
                minimum_turning_radius_m=plan.minimum_turning_radius_m,
                initial_heading_error_deg=(
                    math.degrees(plan.initial_heading_error_rad)
                    if plan.initial_heading_error_rad is not None
                    else None
                ),
                reason=(
                    (
                        "Route is collision-checked and validated for "
                        "the configured steering geometry"
                        + (
                            " using direction-aware Hybrid A* recovery"
                            if plan.planning_method == "hybrid_astar"
                            else "; smoothing is applied"
                        )
                        + (
                            "; no motion command has been issued"
                            if pose_source == "localization"
                            else (
                                "; this raw-odometry preview is diagnostic only; "
                                "review a new route when fused localization is available"
                            )
                        )
                    )
                    if plan.geometry_validated
                    else "Route preview is ready; Ackermann geometry is not configured"
                ),
            )
            return self._status

    async def clear(self) -> NavigationPlanStatus:
        async with self._lock:
            self._status = NavigationPlanStatus.idle()
            return self._status

    def _planning_pose(self, frame_id: str) -> Optional[PlanningPose]:
        localization = self._bus.latest(LOCALIZATION_POSE)
        now_ns = time.monotonic_ns()
        if (
            localization is not None
            and localization.header.frame_id == frame_id
            and 0
            <= now_ns - localization.header.timestamp_monotonic_ns
            <= self._localization_timeout_ns
        ):
            return (
                localization.x_m,
                localization.y_m,
                localization.yaw_rad,
                "localization",
            )
        odometry = self._bus.latest(ODOMETRY)
        if odometry is not None and odometry.header.frame_id == frame_id:
            return odometry.x_m, odometry.y_m, odometry.yaw_rad, "odometry"
        return None

    def _set_rejected(
        self,
        request: NavigationGoalRequest,
        *,
        goal: NavigationPoint,
        reason: str,
        available: bool = True,
        start: Optional[NavigationPoint] = None,
        map_sequence: Optional[int] = None,
        pose_source: Optional[Literal["localization", "odometry"]] = None,
        start_yaw_rad: Optional[float] = None,
        frame_id: str = "odom",
    ) -> NavigationPlanStatus:
        self._status = NavigationPlanStatus(
            available=available,
            state=NavigationPlanState.REJECTED,
            frame_id=frame_id,
            goal=goal,
            start=start,
            clearance_m=request.clearance_m,
            allow_unknown=request.allow_unknown,
            map_sequence=map_sequence,
            pose_source=pose_source,
            start_yaw_rad=start_yaw_rad,
            reason=reason,
        )
        return self._status


__all__ = [
    "GridPlan",
    "NavigationPlanRejected",
    "NavigationPlanningService",
    "OccupancyGridPlanner",
]
