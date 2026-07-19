"""Measured Ackermann geometry and encoder calibration."""

from typing import Optional

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated, Self


class AckermannOdometryConfig(BaseModel):
    enabled: EnabledField = False
    wheelbase_m: Annotated[
        Optional[float],
        Field(
            title="Wheelbase",
            description="Distance in metres between front and rear axle centers.",
            gt=0,
        ),
    ] = None
    wheel_radius_m: Annotated[
        Optional[float],
        Field(
            title="Driven wheel radius",
            description="Effective rolling radius of the driven wheel in metres.",
            gt=0,
        ),
    ] = None
    encoder_ticks_per_revolution: Annotated[
        Optional[int],
        Field(
            title="Encoder ticks per revolution",
            description="Encoder ticks per revolution at the encoder shaft.",
            gt=0,
        ),
    ] = None
    gear_ratio: Annotated[
        float,
        Field(
            title="Encoder-to-wheel gear ratio",
            description="Encoder shaft revolutions per driven-wheel revolution.",
            gt=0,
        ),
    ] = 1.0
    max_steering_age_ms: Annotated[
        int,
        Field(
            title="Maximum steering observation age",
            description="Reject encoder integration when steering state is older.",
            ge=50,
            le=2000,
        ),
    ] = 250

    @model_validator(mode="after")
    def require_geometry_when_enabled(self) -> Self:
        required = {
            "wheelbase_m": self.wheelbase_m,
            "wheel_radius_m": self.wheel_radius_m,
            "encoder_ticks_per_revolution": self.encoder_ticks_per_revolution,
        }
        missing = [name for name, value in required.items() if value is None]
        if self.enabled and missing:
            raise ValueError(
                "Ackermann odometry requires calibrated " + ", ".join(missing)
            )
        return self


__all__ = ["AckermannOdometryConfig"]
