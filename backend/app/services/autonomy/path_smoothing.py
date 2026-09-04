"""Collision-preserving smoothing and Ackermann path feasibility checks."""

import math
from dataclasses import dataclass
from typing import Callable, Sequence, Tuple

from app.schemas.autonomy import NavigationPoint


PathClearanceCheck = Callable[[Sequence[NavigationPoint]], bool]


class PathGeometryRejected(ValueError):
    """The route cannot be made safe for the configured vehicle geometry."""


@dataclass(frozen=True)
class SmoothedPath:
    """A collision-checked route and its Ackermann geometry diagnostics."""

    path: Tuple[NavigationPoint, ...]
    raw_waypoint_count: int
    max_curvature_per_m: float
    curvature_limit_per_m: float
    minimum_turning_radius_m: float
    initial_heading_error_rad: float
    smoothed: bool


class AckermannPathSmoother:
    """Round polyline corners while retaining inflated-map collision safety.

    Chaikin corner cutting is deliberately used as a small, deterministic
    geometry stage rather than as another planner. Every candidate is checked
    against the planner's already-inflated occupancy grid. The least-curved
    collision-free candidate is accepted only when its sampled curvature is
    achievable by the configured steering geometry.
    """

    def __init__(
        self,
        *,
        wheelbase_m: float,
        max_abs_steering_angle_rad: float,
        max_iterations: int = 8,
        corner_cutting_ratio: float = 0.25,
        heading_anchor_m: float = 0.10,
        tracking_lookahead_m: float = 0.25,
        heading_alignment_tolerance_rad: float = math.radians(5.0),
        curvature_sample_spacing_m: float = 0.04,
        curvature_tolerance: float = 0.05,
    ) -> None:
        if wheelbase_m <= 0:
            raise ValueError("wheelbase must be positive")
        if not 0 < max_abs_steering_angle_rad < math.pi / 2:
            raise ValueError("maximum steering angle must be between 0 and pi/2")
        if max_iterations < 0:
            raise ValueError("maximum smoothing iterations cannot be negative")
        if not 0 < corner_cutting_ratio < 0.5:
            raise ValueError("corner-cutting ratio must be between 0 and 0.5")
        if heading_anchor_m <= 0:
            raise ValueError("heading anchor distance must be positive")
        if tracking_lookahead_m <= 0:
            raise ValueError("tracking lookahead must be positive")
        if not 0 <= heading_alignment_tolerance_rad < math.pi / 2:
            raise ValueError("heading-alignment tolerance must be in [0, pi/2)")
        if curvature_sample_spacing_m <= 0:
            raise ValueError("curvature sample spacing must be positive")
        if not 0 <= curvature_tolerance <= 0.25:
            raise ValueError("curvature tolerance must be between 0 and 0.25")
        self.wheelbase_m = wheelbase_m
        self.max_abs_steering_angle_rad = max_abs_steering_angle_rad
        self.max_iterations = max_iterations
        self.corner_cutting_ratio = corner_cutting_ratio
        self.heading_anchor_m = heading_anchor_m
        self.tracking_lookahead_m = tracking_lookahead_m
        self.heading_alignment_tolerance_rad = heading_alignment_tolerance_rad
        minimum_turning_radius_m = wheelbase_m / math.tan(max_abs_steering_angle_rad)
        self.curvature_sample_spacing_m = min(
            curvature_sample_spacing_m,
            minimum_turning_radius_m / 8.0,
        )
        self.curvature_tolerance = curvature_tolerance

    @property
    def curvature_limit_per_m(self) -> float:
        return math.tan(self.max_abs_steering_angle_rad) / self.wheelbase_m

    @property
    def minimum_turning_radius_m(self) -> float:
        return 1.0 / self.curvature_limit_per_m

    def smooth(
        self,
        path: Sequence[NavigationPoint],
        *,
        start_yaw_rad: float,
        is_clear: PathClearanceCheck,
    ) -> SmoothedPath:
        normalized = self._deduplicate(path)
        if len(normalized) < 2:
            raise PathGeometryRejected("route is too short for curvature validation")

        initial_heading_error = self._normalize_angle(
            self._segment_heading(normalized[0], normalized[1]) - start_yaw_rad
        )
        direct_arc = self._direct_tangent_arc(
            normalized,
            start_yaw_rad=start_yaw_rad,
            initial_heading_error_rad=initial_heading_error,
        )
        working = (
            direct_arc
            if direct_arc is not None and is_clear(direct_arc)
            else self._add_heading_anchor(normalized, start_yaw_rad)
        )
        if not is_clear(working):
            # A heading anchor can expose that the grid route starts in a
            # direction the vehicle cannot enter without leaving free space.
            working = normalized

        current_path = working
        best_path = working
        best_curvature = self._sampled_maximum_curvature(working)
        smoothed = False
        for _ in range(self.max_iterations):
            if best_curvature <= self.curvature_limit_per_m:
                break
            candidate = self._chaikin(current_path)
            if not is_clear(candidate):
                break
            current_path = candidate
            candidate_curvature = self._sampled_maximum_curvature(candidate)
            if candidate_curvature < best_curvature:
                best_path = candidate
                best_curvature = candidate_curvature
                smoothed = True

        # A route with an unaligned first segment is not differentiable at the
        # current vehicle pose. When the safe heading anchor could not be used,
        # include that start discontinuity in the feasibility result.
        heading_error_after = self._normalize_angle(
            self._segment_heading(best_path[0], best_path[1]) - start_yaw_rad
        )
        anchor_preserved = (
            abs(heading_error_after) <= self.heading_alignment_tolerance_rad
        )
        if not anchor_preserved:
            if abs(initial_heading_error) > self.heading_alignment_tolerance_rad:
                raise PathGeometryRejected(
                    "route cannot be entered from the current heading while "
                    "preserving obstacle clearance"
                )
            best_curvature = max(
                best_curvature,
                self._heading_discontinuity_curvature(
                    heading_error_after, self._path_length(best_path)
                ),
            )

        curvature_limit = self.curvature_limit_per_m
        if best_curvature > curvature_limit * (1.0 + self.curvature_tolerance):
            required_radius = 0.0 if best_curvature == 0 else 1.0 / best_curvature
            raise PathGeometryRejected(
                "route requires approximately "
                f"{required_radius:.2f} m turning radius, below the configured "
                f"{self.minimum_turning_radius_m:.2f} m minimum"
            )
        sampled_path = self._sample_path(
            best_path, spacing_m=self.curvature_sample_spacing_m
        )
        sampled_curvature = self._maximum_curvature(sampled_path)
        if sampled_curvature > curvature_limit * (1.0 + self.curvature_tolerance):
            required_radius = (
                0.0 if not math.isfinite(sampled_curvature) else 1.0 / sampled_curvature
            )
            raise PathGeometryRejected(
                "route requires approximately "
                f"{required_radius:.2f} m turning radius, below the configured "
                f"{self.minimum_turning_radius_m:.2f} m minimum"
            )
        if not is_clear(sampled_path):
            raise PathGeometryRejected(
                "smoothed route does not preserve the requested obstacle clearance"
            )

        return SmoothedPath(
            path=sampled_path,
            raw_waypoint_count=len(normalized),
            max_curvature_per_m=sampled_curvature,
            curvature_limit_per_m=curvature_limit,
            minimum_turning_radius_m=self.minimum_turning_radius_m,
            initial_heading_error_rad=initial_heading_error,
            smoothed=smoothed or best_path != normalized,
        )

    def _direct_tangent_arc(
        self,
        path: Tuple[NavigationPoint, ...],
        *,
        start_yaw_rad: float,
        initial_heading_error_rad: float,
    ) -> Tuple[NavigationPoint, ...] | None:
        """Return the unique start-tangent circle for a visible direct goal."""

        if (
            len(path) != 2
            or abs(initial_heading_error_rad) <= self.heading_alignment_tolerance_rad
        ):
            return None
        delta_x = path[1].x_m - path[0].x_m
        delta_y = path[1].y_m - path[0].y_m
        cosine = math.cos(start_yaw_rad)
        sine = math.sin(start_yaw_rad)
        forward_m = cosine * delta_x + sine * delta_y
        lateral_m = -sine * delta_x + cosine * delta_y
        chord_squared = forward_m * forward_m + lateral_m * lateral_m
        if chord_squared <= 1e-12 or abs(lateral_m) <= 1e-9:
            return None
        heading_change_rad = 2.0 * math.atan2(lateral_m, forward_m)
        # A forward-only local route must not begin by looping behind itself.
        if abs(heading_change_rad) > math.pi + 1e-9:
            return None
        curvature_per_m = 2.0 * lateral_m / chord_squared
        arc_length_m = abs(heading_change_rad / curvature_per_m)
        sample_count = max(2, math.ceil(arc_length_m / self.curvature_sample_spacing_m))
        result = []
        for sample_index in range(sample_count + 1):
            distance_m = arc_length_m * sample_index / sample_count
            local_x_m = math.sin(curvature_per_m * distance_m) / curvature_per_m
            local_y_m = (1.0 - math.cos(curvature_per_m * distance_m)) / curvature_per_m
            result.append(
                NavigationPoint(
                    x_m=path[0].x_m + cosine * local_x_m - sine * local_y_m,
                    y_m=path[0].y_m + sine * local_x_m + cosine * local_y_m,
                )
            )
        result[-1] = path[-1]
        return tuple(result)

    def _add_heading_anchor(
        self,
        path: Tuple[NavigationPoint, ...],
        start_yaw_rad: float,
    ) -> Tuple[NavigationPoint, ...]:
        heading_error = self._normalize_angle(
            self._segment_heading(path[0], path[1]) - start_yaw_rad
        )
        if abs(heading_error) <= self.heading_alignment_tolerance_rad:
            return path
        first_length = self._distance(path[0], path[1])
        heading_x = math.cos(start_yaw_rad)
        heading_y = math.sin(start_yaw_rad)
        forward_projection = (path[1].x_m - path[0].x_m) * heading_x + (
            path[1].y_m - path[0].y_m
        ) * heading_y
        anchor_distance = min(
            first_length,
            max(self.heading_anchor_m, forward_projection),
        )
        if anchor_distance <= 1e-6:
            return path
        anchor = NavigationPoint(
            x_m=path[0].x_m + anchor_distance * heading_x,
            y_m=path[0].y_m + anchor_distance * heading_y,
        )
        if self._distance(anchor, path[1]) <= 1e-6:
            return path
        return self._deduplicate((path[0], anchor, *path[1:]))

    def _chaikin(
        self, path: Tuple[NavigationPoint, ...]
    ) -> Tuple[NavigationPoint, ...]:
        ratio = self.corner_cutting_ratio
        result = [path[0]]
        for start, end in zip(path, path[1:]):
            result.append(self._interpolate(start, end, ratio))
            result.append(self._interpolate(start, end, 1.0 - ratio))
        result.append(path[-1])
        return self._deduplicate(result)

    def _maximum_curvature(self, path: Sequence[NavigationPoint]) -> float:
        return max(
            (
                self._three_point_curvature(before, point, after)
                for before, point, after in zip(path, path[1:], path[2:])
            ),
            default=0.0,
        )

    def _sampled_maximum_curvature(self, path: Sequence[NavigationPoint]) -> float:
        return self._maximum_curvature(
            self._sample_path(path, spacing_m=self.curvature_sample_spacing_m)
        )

    @staticmethod
    def _sample_path(
        path: Sequence[NavigationPoint], *, spacing_m: float
    ) -> Tuple[NavigationPoint, ...]:
        cumulative = [0.0]
        for start, end in zip(path, path[1:]):
            cumulative.append(
                cumulative[-1] + AckermannPathSmoother._distance(start, end)
            )
        total_length = cumulative[-1]
        if total_length <= 1e-9:
            return tuple(path)

        sample_count = max(1, math.ceil(total_length / spacing_m))
        result = []
        segment_index = 0
        for sample_index in range(sample_count + 1):
            distance = total_length * sample_index / sample_count
            while (
                segment_index < len(path) - 2
                and distance > cumulative[segment_index + 1]
            ):
                segment_index += 1
            segment_start = cumulative[segment_index]
            segment_end = cumulative[segment_index + 1]
            fraction = (
                0.0
                if segment_end - segment_start <= 1e-12
                else (distance - segment_start) / (segment_end - segment_start)
            )
            result.append(
                AckermannPathSmoother._interpolate(
                    path[segment_index], path[segment_index + 1], fraction
                )
            )
        return AckermannPathSmoother._deduplicate(result)

    def _heading_discontinuity_curvature(
        self, heading_error_rad: float, path_length_m: float
    ) -> float:
        target_distance_m = min(self.tracking_lookahead_m, path_length_m)
        if target_distance_m <= 1e-9:
            return math.inf
        return 2.0 * abs(math.sin(heading_error_rad)) / target_distance_m

    @staticmethod
    def _path_length(path: Sequence[NavigationPoint]) -> float:
        return sum(
            AckermannPathSmoother._distance(start, end)
            for start, end in zip(path, path[1:])
        )

    @staticmethod
    def _three_point_curvature(
        before: NavigationPoint,
        point: NavigationPoint,
        after: NavigationPoint,
    ) -> float:
        side_a = AckermannPathSmoother._distance(before, point)
        side_b = AckermannPathSmoother._distance(point, after)
        side_c = AckermannPathSmoother._distance(before, after)
        incoming_x = point.x_m - before.x_m
        incoming_y = point.y_m - before.y_m
        outgoing_x = after.x_m - point.x_m
        outgoing_y = after.y_m - point.y_m
        if incoming_x * outgoing_x + incoming_y * outgoing_y < 0:
            return math.inf
        denominator = side_a * side_b * side_c
        if denominator <= 1e-12:
            return 0.0
        cross = abs(
            (point.x_m - before.x_m) * (after.y_m - before.y_m)
            - (point.y_m - before.y_m) * (after.x_m - before.x_m)
        )
        return 2.0 * cross / denominator

    @staticmethod
    def _deduplicate(
        path: Sequence[NavigationPoint],
    ) -> Tuple[NavigationPoint, ...]:
        result = []
        for point in path:
            if not result or AckermannPathSmoother._distance(result[-1], point) > 1e-9:
                result.append(point)
        return tuple(result)

    @staticmethod
    def _interpolate(
        start: NavigationPoint, end: NavigationPoint, fraction: float
    ) -> NavigationPoint:
        return NavigationPoint(
            x_m=start.x_m + fraction * (end.x_m - start.x_m),
            y_m=start.y_m + fraction * (end.y_m - start.y_m),
        )

    @staticmethod
    def _segment_heading(start: NavigationPoint, end: NavigationPoint) -> float:
        return math.atan2(end.y_m - start.y_m, end.x_m - start.x_m)

    @staticmethod
    def _distance(start: NavigationPoint, end: NavigationPoint) -> float:
        return math.hypot(end.x_m - start.x_m, end.y_m - start.y_m)

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        return (angle + math.pi) % (2.0 * math.pi) - math.pi


__all__ = [
    "AckermannPathSmoother",
    "PathGeometryRejected",
    "SmoothedPath",
]
