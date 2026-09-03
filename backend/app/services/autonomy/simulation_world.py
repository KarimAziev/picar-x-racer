"""Deterministic geometry, collision checks, and ideal 2D LiDAR raycasting."""

import math
from dataclasses import dataclass
from typing import Iterable, Tuple

from app.schemas.autonomy import LaserScan, MessageHeader


@dataclass(frozen=True)
class LineSegment2D:
    start_x_m: float
    start_y_m: float
    end_x_m: float
    end_y_m: float

    def __post_init__(self) -> None:
        values = (
            self.start_x_m,
            self.start_y_m,
            self.end_x_m,
            self.end_y_m,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("simulation world coordinates must be finite")
        if self.start_x_m == self.end_x_m and self.start_y_m == self.end_y_m:
            raise ValueError("simulation world segments must have non-zero length")


@dataclass(frozen=True)
class SimulationWorld:
    scenario: str
    segments: Tuple[LineSegment2D, ...]
    solid_rectangles: Tuple[Tuple[float, float, float, float], ...] = ()

    def __post_init__(self) -> None:
        if not self.scenario.strip():
            raise ValueError("simulation world scenario must not be empty")
        if not self.segments:
            raise ValueError("simulation world must contain at least one segment")
        for left, bottom, right, top in self.solid_rectangles:
            if not all(math.isfinite(value) for value in (left, bottom, right, top)):
                raise ValueError("simulation obstacle bounds must be finite")
            if right <= left or top <= bottom:
                raise ValueError("simulation obstacle bounds must have positive area")

    def collides_circle(self, x_m: float, y_m: float, radius_m: float) -> bool:
        if not all(math.isfinite(value) for value in (x_m, y_m, radius_m)):
            raise ValueError("collision geometry must be finite")
        if radius_m <= 0:
            raise ValueError("collision radius must be greater than zero")
        radius_squared = radius_m * radius_m
        if any(
            _point_rectangle_distance_squared(x_m, y_m, rectangle) <= radius_squared
            for rectangle in self.solid_rectangles
        ):
            return True
        return any(
            _point_segment_distance_squared(x_m, y_m, segment) <= radius_squared
            for segment in self.segments
        )

    def distance_to_nearest_segment(self, x_m: float, y_m: float) -> float:
        """Return Euclidean distance to the closest known-world line segment."""

        if not math.isfinite(x_m) or not math.isfinite(y_m):
            raise ValueError("world query coordinates must be finite")
        return math.sqrt(
            min(
                _point_segment_distance_squared(x_m, y_m, segment)
                for segment in self.segments
            )
        )


@dataclass(frozen=True)
class RaycastLidarConfig:
    frame_id: str
    sensor_x_m: float
    sensor_y_m: float
    sensor_yaw_rad: float
    range_min_m: float
    range_max_m: float
    angular_resolution_deg: float
    scan_frequency_hz: float = 10.0
    quality: int = 100

    def __post_init__(self) -> None:
        values = (
            self.sensor_x_m,
            self.sensor_y_m,
            self.sensor_yaw_rad,
            self.range_min_m,
            self.range_max_m,
            self.angular_resolution_deg,
            self.scan_frequency_hz,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("simulated LiDAR configuration must be finite")
        if not self.frame_id.strip() or self.frame_id.startswith("/"):
            raise ValueError("simulated LiDAR frame_id must be non-empty and relative")
        if self.range_min_m < 0 or self.range_max_m <= self.range_min_m:
            raise ValueError("simulated LiDAR range limits are invalid")
        if self.angular_resolution_deg <= 0 or self.angular_resolution_deg > 45:
            raise ValueError("simulated LiDAR angular resolution is invalid")
        if self.scan_frequency_hz <= 0:
            raise ValueError("simulated LiDAR scan frequency must be positive")
        if not 0 <= self.quality <= 255:
            raise ValueError("simulated LiDAR quality must be between 0 and 255")

    @property
    def bin_count(self) -> int:
        return max(1, round(360.0 / self.angular_resolution_deg))

    @property
    def angle_increment_rad(self) -> float:
        return 2 * math.pi / self.bin_count

    @property
    def scan_period_ns(self) -> int:
        return max(1, round(1_000_000_000 / self.scan_frequency_hz))


class WorldLidarRaycaster:
    """Generate ideal nearest-hit scans from a fixed line-segment world."""

    def __init__(self, world: SimulationWorld, config: RaycastLidarConfig) -> None:
        self.world = world
        self.config = config

    def scan(
        self,
        *,
        base_x_m: float,
        base_y_m: float,
        base_yaw_rad: float,
        timestamp_ns: int,
        sequence: int,
    ) -> LaserScan:
        cos_yaw = math.cos(base_yaw_rad)
        sin_yaw = math.sin(base_yaw_rad)
        sensor_x = (
            base_x_m
            + cos_yaw * self.config.sensor_x_m
            - sin_yaw * self.config.sensor_y_m
        )
        sensor_y = (
            base_y_m
            + sin_yaw * self.config.sensor_x_m
            + cos_yaw * self.config.sensor_y_m
        )
        sensor_yaw = base_yaw_rad + self.config.sensor_yaw_rad
        ranges = []
        intensities = []
        for index in range(self.config.bin_count):
            angle = sensor_yaw + index * self.config.angle_increment_rad
            distance = self._nearest_hit(sensor_x, sensor_y, angle)
            if (
                distance is None
                or distance < self.config.range_min_m
                or distance > self.config.range_max_m
            ):
                ranges.append(math.inf)
                intensities.append(0.0)
            else:
                ranges.append(distance)
                intensities.append(float(self.config.quality))
        return LaserScan(
            header=MessageHeader(
                sequence=sequence,
                frame_id=self.config.frame_id,
                timestamp_monotonic_ns=timestamp_ns,
                source_timestamp_ns=timestamp_ns,
            ),
            angle_min_rad=0.0,
            angle_max_rad=(self.config.bin_count - 1) * self.config.angle_increment_rad,
            angle_increment_rad=self.config.angle_increment_rad,
            range_min_m=self.config.range_min_m,
            range_max_m=self.config.range_max_m,
            ranges_m=tuple(ranges),
            intensities=tuple(intensities),
        )

    def _nearest_hit(
        self, origin_x: float, origin_y: float, angle: float
    ) -> float | None:
        ray_x = math.cos(angle)
        ray_y = math.sin(angle)
        nearest = math.inf
        for segment in self.world.segments:
            segment_x = segment.end_x_m - segment.start_x_m
            segment_y = segment.end_y_m - segment.start_y_m
            denominator = _cross(ray_x, ray_y, segment_x, segment_y)
            if abs(denominator) < 1e-12:
                continue
            offset_x = segment.start_x_m - origin_x
            offset_y = segment.start_y_m - origin_y
            distance = _cross(offset_x, offset_y, segment_x, segment_y) / denominator
            segment_fraction = _cross(offset_x, offset_y, ray_x, ray_y) / denominator
            if distance >= 0 and 0 <= segment_fraction <= 1:
                nearest = min(nearest, distance)
        return nearest if math.isfinite(nearest) else None


def build_simulation_world(
    scenario: str,
    *,
    width_m: float,
    height_m: float,
) -> SimulationWorld:
    """Build one deterministic development world centered on the world origin."""

    if not math.isfinite(width_m) or not math.isfinite(height_m):
        raise ValueError("simulation world dimensions must be finite")
    if width_m <= 0 or height_m <= 0:
        raise ValueError("simulation world dimensions must be positive")
    half_width = width_m / 2
    half_height = height_m / 2
    segments = list(
        _rectangle_segments(-half_width, -half_height, half_width, half_height)
    )
    solid_rectangles = []
    if scenario == "empty_room":
        pass
    elif scenario == "single_obstacle":
        obstacle_left = min(1.35, half_width * 0.45)
        obstacle_right = min(1.85, half_width * 0.75)
        obstacle_half_height = min(0.6, half_height * 0.3)
        segments.extend(
            _rectangle_segments(
                obstacle_left,
                -obstacle_half_height,
                obstacle_right,
                obstacle_half_height,
            )
        )
        solid_rectangles.append(
            (
                obstacle_left,
                -obstacle_half_height,
                obstacle_right,
                obstacle_half_height,
            )
        )
    elif scenario == "corridor":
        corridor_half_width = min(0.75, half_height * 0.45)
        corridor_start = -half_width * 0.55
        corridor_end = half_width * 0.65
        segments.extend(
            (
                LineSegment2D(
                    corridor_start,
                    -corridor_half_width,
                    corridor_end,
                    -corridor_half_width,
                ),
                LineSegment2D(
                    corridor_start,
                    corridor_half_width,
                    corridor_end,
                    corridor_half_width,
                ),
            )
        )
    else:
        raise ValueError(f"unsupported simulation world scenario: {scenario}")
    return SimulationWorld(
        scenario=scenario,
        segments=tuple(segments),
        solid_rectangles=tuple(solid_rectangles),
    )


def _rectangle_segments(
    left: float,
    bottom: float,
    right: float,
    top: float,
) -> Iterable[LineSegment2D]:
    if right <= left or top <= bottom:
        raise ValueError("simulation rectangles must have positive dimensions")
    return (
        LineSegment2D(left, bottom, right, bottom),
        LineSegment2D(right, bottom, right, top),
        LineSegment2D(right, top, left, top),
        LineSegment2D(left, top, left, bottom),
    )


def _point_segment_distance_squared(
    point_x: float,
    point_y: float,
    segment: LineSegment2D,
) -> float:
    segment_x = segment.end_x_m - segment.start_x_m
    segment_y = segment.end_y_m - segment.start_y_m
    length_squared = segment_x * segment_x + segment_y * segment_y
    projection = (
        (point_x - segment.start_x_m) * segment_x
        + (point_y - segment.start_y_m) * segment_y
    ) / length_squared
    clamped = max(0.0, min(1.0, projection))
    closest_x = segment.start_x_m + clamped * segment_x
    closest_y = segment.start_y_m + clamped * segment_y
    delta_x = point_x - closest_x
    delta_y = point_y - closest_y
    return delta_x * delta_x + delta_y * delta_y


def _point_rectangle_distance_squared(
    point_x: float,
    point_y: float,
    rectangle: Tuple[float, float, float, float],
) -> float:
    left, bottom, right, top = rectangle
    delta_x = max(left - point_x, 0.0, point_x - right)
    delta_y = max(bottom - point_y, 0.0, point_y - top)
    return delta_x * delta_x + delta_y * delta_y


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


__all__ = [
    "LineSegment2D",
    "RaycastLidarConfig",
    "SimulationWorld",
    "WorldLidarRaycaster",
    "build_simulation_world",
]
