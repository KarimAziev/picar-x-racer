"""Configuration for LiDAR-derived motion safety constraints."""

from typing import Optional

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated, Self


class LidarSafetyConfig(BaseModel):
    """Directional speed limits derived from fresh front and rear LiDAR returns."""

    enabled: EnabledField = Field(
        default=False,
        description="Use LiDAR to slow or stop near obstacles. Requires Motion control, LiDAR, and both distance limits below. Restart the backend after enabling.",
    )
    front_half_angle_deg: Annotated[
        float,
        Field(
            title="Safety sector half-angle (degrees)",
            description="How far to look to each side of straight ahead and straight behind. 35 degrees checks a 70-degree-wide area in each direction.",
            gt=0,
            le=90,
            allow_inf_nan=False,
        ),
    ] = 35.0
    stop_distance_m: Annotated[
        Optional[float],
        Field(
            title="Directional stop distance (m)",
            description="Block driving toward an obstacle this close to the robot reference point at the rear axle. Include the body overhang and room to stop; 0.3 m means 30 cm.",
            gt=0,
            allow_inf_nan=False,
        ),
    ] = None
    slow_distance_m: Annotated[
        Optional[float],
        Field(
            title="Directional slowdown distance (m)",
            description="Begin reducing speed when an obstacle comes within this distance of the rear-axle reference point. Set this farther away than the stop distance.",
            gt=0,
            allow_inf_nan=False,
        ),
    ] = None
    scan_timeout_ms: Annotated[
        int,
        Field(
            title="LiDAR scan timeout (ms)",
            description="Block forward and reverse driving if no new LiDAR scan arrives within this time. 500 ms is half a second.",
            ge=100,
            le=5000,
        ),
    ] = 500
    min_obstacle_points: Annotated[
        int,
        Field(
            title="Minimum obstacle returns",
            description="Number of nearby LiDAR points needed to limit speed. 2 ignores a single stray point; larger values can miss small obstacles.",
            ge=1,
            le=20,
        ),
    ] = 2

    @model_validator(mode="after")
    def validate_distances(self) -> Self:
        if self.enabled and (
            self.stop_distance_m is None or self.slow_distance_m is None
        ):
            raise ValueError(
                "Before enabling LiDAR directional safety, enter Directional stop distance (m) "
                "and Directional slowdown distance (m)."
            )
        if (
            self.stop_distance_m is not None
            and self.slow_distance_m is not None
            and self.slow_distance_m <= self.stop_distance_m
        ):
            raise ValueError(
                "Directional slowdown distance (m) must be greater than Directional stop distance (m)."
            )
        return self


__all__ = ["LidarSafetyConfig"]
