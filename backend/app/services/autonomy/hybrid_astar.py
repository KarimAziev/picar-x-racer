"""Bounded direction-aware Hybrid A* recovery for Ackermann navigation paths."""

import heapq
import math
from dataclasses import dataclass
from itertools import count
from typing import Dict, List, Optional, Sequence, Tuple

from app.schemas.autonomy import NavigationDirection, NavigationPoint
from app.services.autonomy.path_smoothing import PathClearanceCheck


HybridStateKey = Tuple[int, int, int, int]


class HybridPathNotFound(ValueError):
    """No bounded Ackermann path reached the selected goal."""


@dataclass(frozen=True)
class HybridPose:
    x_m: float
    y_m: float
    yaw_rad: float


@dataclass(frozen=True)
class HybridPath:
    path: Tuple[NavigationPoint, ...]
    path_directions: Tuple[NavigationDirection, ...]
    expanded_nodes: int
    max_curvature_per_m: float

    @property
    def reverse_distance_m(self) -> float:
        return sum(
            math.hypot(end.x_m - start.x_m, end.y_m - start.y_m)
            for start, end, direction in zip(
                self.path,
                self.path[1:],
                self.path_directions,
            )
            if direction == NavigationDirection.REVERSE
        )

    @property
    def gear_changes(self) -> int:
        return sum(
            before != after
            for before, after in zip(
                self.path_directions,
                self.path_directions[1:],
            )
        )


@dataclass(frozen=True)
class _SearchNode:
    pose: HybridPose
    cost_m: float
    parent_index: Optional[int]
    segment: Tuple[NavigationPoint, ...]
    curvature_per_m: float
    direction: Optional[NavigationDirection]


@dataclass(frozen=True)
class _AnalyticConnection:
    segment: Tuple[NavigationPoint, ...]
    direction: NavigationDirection
    length_m: float
    curvature_per_m: float


class HybridAStarPlanner:
    """Search position and heading with collision-checked bicycle primitives."""

    def __init__(
        self,
        *,
        curvature_limit_per_m: float,
        heading_bins: int = 48,
        max_expanded_nodes: int = 60_000,
        heuristic_weight: float = 1.15,
        analytic_expansion_distance_m: float = 1.25,
        reverse_cost_multiplier: float = 1.25,
        gear_change_penalty_m: float = 0.4,
    ) -> None:
        if curvature_limit_per_m <= 0:
            raise ValueError("curvature limit must be positive")
        if heading_bins < 8:
            raise ValueError("Hybrid A* requires at least eight heading bins")
        if max_expanded_nodes <= 0:
            raise ValueError("maximum expanded-node count must be positive")
        if heuristic_weight < 1:
            raise ValueError("heuristic weight must be at least one")
        if analytic_expansion_distance_m <= 0:
            raise ValueError("analytic expansion distance must be positive")
        if reverse_cost_multiplier < 1:
            raise ValueError("reverse cost multiplier must be at least one")
        if gear_change_penalty_m < 0:
            raise ValueError("gear-change penalty must be non-negative")
        self.curvature_limit_per_m = curvature_limit_per_m
        self.heading_bins = heading_bins
        self.max_expanded_nodes = max_expanded_nodes
        self.heuristic_weight = heuristic_weight
        self.analytic_expansion_distance_m = analytic_expansion_distance_m
        self.reverse_cost_multiplier = reverse_cost_multiplier
        self.gear_change_penalty_m = gear_change_penalty_m

    def plan(
        self,
        *,
        start: HybridPose,
        goal: NavigationPoint,
        grid_resolution_m: float,
        is_clear: PathClearanceCheck,
        guide_path: Sequence[NavigationPoint] = (),
    ) -> HybridPath:
        if grid_resolution_m <= 0:
            raise ValueError("grid resolution must be positive")
        start_point = NavigationPoint(x_m=start.x_m, y_m=start.y_m)

        primitive_length_m = min(
            0.25,
            max(
                grid_resolution_m * 1.5,
                min(0.15, 0.35 / self.curvature_limit_per_m),
            ),
        )
        collision_spacing_m = min(
            grid_resolution_m * 0.25,
            0.1 / self.curvature_limit_per_m,
        )
        analytic_distance_m = max(
            self.analytic_expansion_distance_m,
            4.0 / self.curvature_limit_per_m,
        )
        primitive_curvatures = (
            -self.curvature_limit_per_m,
            -0.5 * self.curvature_limit_per_m,
            0.0,
            0.5 * self.curvature_limit_per_m,
            self.curvature_limit_per_m,
        )

        start_node = _SearchNode(
            pose=start,
            cost_m=0.0,
            parent_index=None,
            segment=(start_point,),
            curvature_per_m=0.0,
            direction=None,
        )
        nodes = [start_node]
        start_key = self._state_key(start, grid_resolution_m)
        best_cost: Dict[HybridStateKey, float] = {start_key: 0.0}
        frontier: List[Tuple[float, float, int, int]] = []
        order = count()
        heapq.heappush(
            frontier,
            (
                self._heuristic(start, goal, guide_path),
                0.0,
                next(order),
                0,
            ),
        )
        expanded = 0

        while frontier and expanded < self.max_expanded_nodes:
            _, queued_cost, _, node_index = heapq.heappop(frontier)
            node = nodes[node_index]
            node_key = self._state_key(
                node.pose,
                grid_resolution_m,
                node.direction,
            )
            if queued_cost > best_cost.get(node_key, math.inf) + 1e-9:
                continue
            expanded += 1

            distance_to_goal = math.hypot(
                goal.x_m - node.pose.x_m,
                goal.y_m - node.pose.y_m,
            )
            if distance_to_goal <= analytic_distance_m:
                analytic = self._best_analytic_connection(
                    node,
                    goal,
                    sample_spacing_m=collision_spacing_m,
                    is_clear=is_clear,
                )
                if analytic is not None:
                    return self._reconstruct(nodes, node_index, analytic, expanded)

            for direction in (
                NavigationDirection.FORWARD,
                NavigationDirection.REVERSE,
            ):
                direction_sign = self._direction_sign(direction)
                for curvature_per_m in primitive_curvatures:
                    segment, end_pose = self._rollout(
                        node.pose,
                        curvature_per_m=curvature_per_m,
                        distance_m=direction_sign * primitive_length_m,
                        sample_spacing_m=collision_spacing_m,
                    )
                    if not is_clear(segment):
                        continue
                    state_key = self._state_key(
                        end_pose,
                        grid_resolution_m,
                        direction,
                    )
                    steering_fraction = abs(
                        curvature_per_m / self.curvature_limit_per_m
                    )
                    steering_change = (
                        abs(curvature_per_m - node.curvature_per_m)
                        / self.curvature_limit_per_m
                    )
                    candidate_cost = node.cost_m + self._motion_cost(
                        primitive_length_m,
                        direction=direction,
                        previous_direction=node.direction,
                        steering_fraction=steering_fraction,
                        steering_change=steering_change,
                    )
                    if candidate_cost >= best_cost.get(state_key, math.inf) - 1e-9:
                        continue
                    best_cost[state_key] = candidate_cost
                    candidate_index = len(nodes)
                    nodes.append(
                        _SearchNode(
                            pose=end_pose,
                            cost_m=candidate_cost,
                            parent_index=node_index,
                            segment=segment,
                            curvature_per_m=curvature_per_m,
                            direction=direction,
                        )
                    )
                    heuristic = self._heuristic(end_pose, goal, guide_path)
                    heapq.heappush(
                        frontier,
                        (
                            candidate_cost + self.heuristic_weight * heuristic,
                            candidate_cost,
                            next(order),
                            candidate_index,
                        ),
                    )

        if expanded >= self.max_expanded_nodes:
            raise HybridPathNotFound(
                "curvature-aware search reached its interactive expansion limit"
            )
        raise HybridPathNotFound("no direction-aware Ackermann route reaches the goal")

    def _rollout(
        self,
        pose: HybridPose,
        *,
        curvature_per_m: float,
        distance_m: float,
        sample_spacing_m: float,
    ) -> Tuple[Tuple[NavigationPoint, ...], HybridPose]:
        sample_count = max(1, math.ceil(abs(distance_m) / sample_spacing_m))
        segment = []
        end_pose = pose
        for sample_index in range(sample_count + 1):
            traveled_m = distance_m * sample_index / sample_count
            end_pose = self._integrate(pose, curvature_per_m, traveled_m)
            segment.append(NavigationPoint(x_m=end_pose.x_m, y_m=end_pose.y_m))
        return tuple(segment), end_pose

    def _best_analytic_connection(
        self,
        node: _SearchNode,
        goal: NavigationPoint,
        *,
        sample_spacing_m: float,
        is_clear: PathClearanceCheck,
    ) -> Optional[_AnalyticConnection]:
        candidates = []
        for direction in (
            NavigationDirection.FORWARD,
            NavigationDirection.REVERSE,
        ):
            connection = self._analytic_connection(
                node.pose,
                goal,
                direction=direction,
                sample_spacing_m=sample_spacing_m,
            )
            if connection is None or not is_clear(connection.segment):
                continue
            candidates.append(
                (
                    self._motion_cost(
                        connection.length_m,
                        direction=direction,
                        previous_direction=node.direction,
                        steering_fraction=abs(
                            connection.curvature_per_m / self.curvature_limit_per_m
                        ),
                        steering_change=(
                            abs(connection.curvature_per_m - node.curvature_per_m)
                            / self.curvature_limit_per_m
                        ),
                    ),
                    connection,
                )
            )
        return min(candidates, key=lambda item: item[0])[1] if candidates else None

    def _analytic_connection(
        self,
        pose: HybridPose,
        goal: NavigationPoint,
        *,
        direction: NavigationDirection,
        sample_spacing_m: float,
    ) -> Optional[_AnalyticConnection]:
        delta_x = goal.x_m - pose.x_m
        delta_y = goal.y_m - pose.y_m
        distance_squared = delta_x * delta_x + delta_y * delta_y
        if distance_squared <= 1e-12:
            point = NavigationPoint(x_m=pose.x_m, y_m=pose.y_m)
            return _AnalyticConnection(
                segment=(point, goal),
                direction=direction,
                length_m=0.0,
                curvature_per_m=0.0,
            )

        direction_sign = self._direction_sign(direction)
        travel_yaw = pose.yaw_rad + (math.pi if direction_sign < 0 else 0.0)
        cosine = math.cos(travel_yaw)
        sine = math.sin(travel_yaw)
        forward_m = cosine * delta_x + sine * delta_y
        lateral_m = -sine * delta_x + cosine * delta_y
        if abs(lateral_m) <= 1e-9:
            if forward_m <= 0:
                return None
            path_curvature_per_m = 0.0
            arc_length_m = forward_m
        else:
            path_curvature_per_m = 2.0 * lateral_m / distance_squared
            if abs(path_curvature_per_m) > self.curvature_limit_per_m * 1.001:
                return None
            heading_change_rad = 2.0 * math.atan2(lateral_m, forward_m)
            if abs(heading_change_rad) > math.pi + 1e-9:
                return None
            arc_length_m = abs(heading_change_rad / path_curvature_per_m)

        sample_count = max(1, math.ceil(arc_length_m / sample_spacing_m))
        result = []
        vehicle_curvature_per_m = direction_sign * path_curvature_per_m
        for sample_index in range(sample_count + 1):
            traveled_m = arc_length_m * sample_index / sample_count
            sampled_pose = self._integrate(
                pose,
                vehicle_curvature_per_m,
                direction_sign * traveled_m,
            )
            result.append(NavigationPoint(x_m=sampled_pose.x_m, y_m=sampled_pose.y_m))
        result[-1] = goal
        return _AnalyticConnection(
            segment=tuple(result),
            direction=direction,
            length_m=arc_length_m,
            curvature_per_m=vehicle_curvature_per_m,
        )

    @staticmethod
    def _integrate(
        pose: HybridPose, curvature_per_m: float, distance_m: float
    ) -> HybridPose:
        if abs(curvature_per_m) <= 1e-12:
            return HybridPose(
                x_m=pose.x_m + distance_m * math.cos(pose.yaw_rad),
                y_m=pose.y_m + distance_m * math.sin(pose.yaw_rad),
                yaw_rad=pose.yaw_rad,
            )
        end_yaw = pose.yaw_rad + curvature_per_m * distance_m
        return HybridPose(
            x_m=pose.x_m
            + (math.sin(end_yaw) - math.sin(pose.yaw_rad)) / curvature_per_m,
            y_m=pose.y_m
            + (-math.cos(end_yaw) + math.cos(pose.yaw_rad)) / curvature_per_m,
            yaw_rad=HybridAStarPlanner._normalize_angle(end_yaw),
        )

    def _state_key(
        self,
        pose: HybridPose,
        grid_resolution_m: float,
        direction: Optional[NavigationDirection] = None,
    ) -> HybridStateKey:
        normalized_yaw = self._normalize_angle(pose.yaw_rad)
        heading_index = (
            round((normalized_yaw + math.pi) / (2.0 * math.pi) * self.heading_bins)
            % self.heading_bins
        )
        return (
            round(pose.x_m / grid_resolution_m),
            round(pose.y_m / grid_resolution_m),
            heading_index,
            self._direction_sign(direction) if direction is not None else 0,
        )

    def _motion_cost(
        self,
        distance_m: float,
        *,
        direction: NavigationDirection,
        previous_direction: Optional[NavigationDirection],
        steering_fraction: float,
        steering_change: float,
    ) -> float:
        direction_multiplier = (
            self.reverse_cost_multiplier
            if direction == NavigationDirection.REVERSE
            else 1.0
        )
        gear_change_cost = (
            self.gear_change_penalty_m
            if previous_direction is not None and previous_direction != direction
            else 0.0
        )
        return (
            distance_m
            * direction_multiplier
            * (1.0 + 0.06 * steering_fraction + 0.03 * steering_change)
            + gear_change_cost
        )

    @staticmethod
    def _heuristic(
        pose: HybridPose,
        goal: NavigationPoint,
        guide_path: Sequence[NavigationPoint],
    ) -> float:
        goal_distance = math.hypot(goal.x_m - pose.x_m, goal.y_m - pose.y_m)
        if not guide_path:
            return goal_distance
        guide_distance = min(
            math.hypot(point.x_m - pose.x_m, point.y_m - pose.y_m)
            for point in guide_path
        )
        return goal_distance + 0.20 * guide_distance

    @staticmethod
    def _reconstruct(
        nodes: Sequence[_SearchNode],
        node_index: int,
        analytic: _AnalyticConnection,
        expanded_nodes: int,
    ) -> HybridPath:
        segments = []
        while node_index != 0:
            node = nodes[node_index]
            segments.append(node)
            if node.parent_index is None:
                break
            node_index = node.parent_index
        segments.reverse()
        path = [nodes[0].segment[0]]
        directions = []
        max_curvature_per_m = 0.0
        for segment in segments:
            if segment.direction is None:
                continue
            path.extend(segment.segment[1:])
            directions.extend([segment.direction] * (len(segment.segment) - 1))
            max_curvature_per_m = max(
                max_curvature_per_m,
                abs(segment.curvature_per_m),
            )
        path.extend(analytic.segment[1:])
        directions.extend([analytic.direction] * (len(analytic.segment) - 1))
        max_curvature_per_m = max(
            max_curvature_per_m,
            abs(analytic.curvature_per_m),
        )
        return HybridPath(
            path=tuple(path),
            path_directions=tuple(directions),
            expanded_nodes=expanded_nodes,
            max_curvature_per_m=max_curvature_per_m,
        )

    @staticmethod
    def _direction_sign(direction: NavigationDirection) -> int:
        return 1 if direction == NavigationDirection.FORWARD else -1

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2.0 * math.pi) - math.pi


__all__ = [
    "HybridAStarPlanner",
    "HybridPath",
    "HybridPathNotFound",
    "HybridPose",
]
