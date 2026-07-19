"""Configuration for the native local occupancy grid."""

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field
from typing_extensions import Annotated


class LocalMappingConfig(BaseModel):
    enabled: EnabledField = False
    width_m: Annotated[float, Field(gt=1, le=50, allow_inf_nan=False)] = 10.0
    height_m: Annotated[float, Field(gt=1, le=50, allow_inf_nan=False)] = 10.0
    resolution_m: Annotated[float, Field(ge=0.01, le=0.5, allow_inf_nan=False)] = 0.05
    max_odometry_age_ms: Annotated[int, Field(ge=20, le=2000)] = 250


__all__ = ["LocalMappingConfig"]
