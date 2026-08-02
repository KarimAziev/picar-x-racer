"""Calibration from absolute linkage position to signed road-wheel steering."""

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class SteeringCalibrationPoint:
    """One measured linkage offset and corresponding signed wheel angle."""

    sensor_offset_deg: float
    wheel_angle_rad: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.sensor_offset_deg):
            raise ValueError("sensor_offset_deg must be finite")
        if not math.isfinite(self.wheel_angle_rad):
            raise ValueError("wheel_angle_rad must be finite")


@dataclass(frozen=True)
class SteeringAngleCalibration:
    """Convert a `[0, 360)` linkage bearing to signed wheel radians.

    With no calibration points, the centered sensor offset is multiplied by
    ``wheel_degrees_per_sensor_degree``. Two or more points enable piecewise
    linear correction for servo/linkage nonlinearity. Point offsets are defined
    after optional direction inversion and must be strictly increasing.
    """

    center_angle_deg: float
    invert_direction: bool = False
    wheel_degrees_per_sensor_degree: float = 1.0
    points: Tuple[SteeringCalibrationPoint, ...] = ()

    def __post_init__(self) -> None:
        if not math.isfinite(self.center_angle_deg):
            raise ValueError("center_angle_deg must be finite")
        if (
            not math.isfinite(self.wheel_degrees_per_sensor_degree)
            or self.wheel_degrees_per_sensor_degree <= 0
        ):
            raise ValueError(
                "wheel_degrees_per_sensor_degree must be finite and positive"
            )
        if len(self.points) == 1:
            raise ValueError(
                "steering calibration requires zero or at least two points"
            )
        previous_offset: float | None = None
        for point in self.points:
            if (
                previous_offset is not None
                and point.sensor_offset_deg <= previous_offset
            ):
                raise ValueError(
                    "steering calibration sensor offsets must increase strictly"
                )
            previous_offset = point.sensor_offset_deg

    def to_wheel_angle_rad(self, absolute_angle_deg: float) -> float:
        """Return signed physical steering, rejecting extrapolation ambiguity."""

        if not math.isfinite(absolute_angle_deg):
            raise ValueError("absolute_angle_deg must be finite")
        offset_deg = (
            absolute_angle_deg - self.center_angle_deg + 180.0
        ) % 360.0 - 180.0
        if self.invert_direction:
            offset_deg = -offset_deg
        if not self.points:
            return math.radians(offset_deg * self.wheel_degrees_per_sensor_degree)
        return self._interpolate(offset_deg)

    def _interpolate(self, sensor_offset_deg: float) -> float:
        first = self.points[0]
        last = self.points[-1]
        if not first.sensor_offset_deg <= sensor_offset_deg <= last.sensor_offset_deg:
            raise ValueError(
                "measured steering position is outside the calibrated linkage range"
            )
        for left, right in zip(self.points, self.points[1:]):
            if sensor_offset_deg <= right.sensor_offset_deg:
                span = right.sensor_offset_deg - left.sensor_offset_deg
                fraction = (sensor_offset_deg - left.sensor_offset_deg) / span
                return left.wheel_angle_rad + fraction * (
                    right.wheel_angle_rad - left.wheel_angle_rad
                )
        return last.wheel_angle_rad


__all__ = ["SteeringAngleCalibration", "SteeringCalibrationPoint"]
