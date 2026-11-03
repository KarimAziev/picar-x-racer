"""Configuration for the native local occupancy grid."""

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field
from typing_extensions import Annotated


class LocalMappingConfig(BaseModel):
    """Robot-centered occupancy grid built from LiDAR and odometry updates."""

    enabled: EnabledField = Field(
        default=False,
        description="Build the map while you drive. Requires Motion control, LiDAR, and Ackermann odometry. Save and restart the backend after enabling; then start a mapping session in Autonomy.",
    )
    width_m: Annotated[
        float,
        Field(
            title="Map width (m)",
            description="Distance covered along the map X axis, centered on the starting position. 10 m covers 5 m on each side; a larger map uses more memory.",
            gt=1,
            le=50,
            allow_inf_nan=False,
        ),
    ] = 10.0
    height_m: Annotated[
        float,
        Field(
            title="Map height (m)",
            description="Distance covered along the map Y axis, centered on the starting position. This is a top-down map dimension, not wall height.",
            gt=1,
            le=50,
            allow_inf_nan=False,
        ),
    ] = 10.0
    resolution_m: Annotated[
        float,
        Field(
            title="Map square size (m)",
            description="Size of one square on the map. 0.05 m means 5 cm squares. Smaller squares show finer detail but use more memory and processing.",
            ge=0.01,
            le=0.5,
            allow_inf_nan=False,
        ),
    ] = 0.05
    max_odometry_age_ms: Annotated[
        int,
        Field(
            title="Position update timeout (ms)",
            description="Skip a LiDAR scan if the latest wheel-based position update is older than this limit. 250 ms is a quarter of a second. This prevents drawing obstacles using an outdated robot position.",
            ge=20,
            le=2000,
        ),
    ] = 250


__all__ = ["LocalMappingConfig"]
