"""Configuration for LiDAR-derived motion safety constraints."""

from typing import Optional

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated, Self


class LidarSafetyConfig(BaseModel):
    """Directional speed limits derived from fresh front and rear LiDAR returns."""

    enabled: EnabledField = False
    front_half_angle_deg: Annotated[
        float,
        Field(
            title="Safety sector half-angle",
            description="Angular half-width used for both front and rear safety sectors.",
            gt=0,
            le=90,
            allow_inf_nan=False,
        ),
    ] = 35.0
    stop_distance_m: Annotated[
        Optional[float],
        Field(
            title="Directional stop distance",
            description="Confirmed obstacles at or inside this distance block motion toward them.",
            gt=0,
            allow_inf_nan=False,
        ),
    ] = None
    slow_distance_m: Annotated[
        Optional[float],
        Field(
            title="Directional slowdown distance",
            description="Speed is reduced between stop and slowdown distance in either direction.",
            gt=0,
            allow_inf_nan=False,
        ),
    ] = None
    scan_timeout_ms: Annotated[
        int,
        Field(
            title="LiDAR scan timeout",
            description="Block forward and reverse motion when a fresh scan is not received.",
            ge=100,
            le=5000,
        ),
    ] = 500
    min_obstacle_points: Annotated[
        int,
        Field(
            title="Minimum obstacle returns",
            description="Nearest-return rank used to reject isolated scan noise.",
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
                "LiDAR safety requires measured stop_distance_m and slow_distance_m"
            )
        if (
            self.stop_distance_m is not None
            and self.slow_distance_m is not None
            and self.slow_distance_m <= self.stop_distance_m
        ):
            raise ValueError("slow_distance_m must be greater than stop_distance_m")
        return self


__all__ = ["LidarSafetyConfig"]
