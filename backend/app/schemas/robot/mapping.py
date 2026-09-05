"""Configuration for the native local occupancy grid."""

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field
from typing_extensions import Annotated


class LocalMappingConfig(BaseModel):
    """Robot-centered occupancy grid built from LiDAR and odometry updates."""

    enabled: EnabledField = False
    width_m: Annotated[
        float,
        Field(
            title="Map width",
            description="Total occupancy-grid width in metres.",
            gt=1,
            le=50,
            allow_inf_nan=False,
        ),
    ] = 10.0
    height_m: Annotated[
        float,
        Field(
            title="Map height",
            description="Total occupancy-grid height in metres.",
            gt=1,
            le=50,
            allow_inf_nan=False,
        ),
    ] = 10.0
    resolution_m: Annotated[
        float,
        Field(
            title="Map resolution",
            description="Width and height of each occupancy-grid cell in metres.",
            ge=0.01,
            le=0.5,
            allow_inf_nan=False,
        ),
    ] = 0.05
    max_odometry_age_ms: Annotated[
        int,
        Field(
            title="Maximum odometry age",
            description="Ignore LiDAR scans when the latest odometry is older.",
            ge=20,
            le=2000,
        ),
    ] = 250


__all__ = ["LocalMappingConfig"]
