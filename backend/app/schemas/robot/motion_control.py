"""Configuration needed to safely translate and execute physical motion."""

from typing import Optional

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated, Self


class MotionControlConfig(BaseModel):
    """Opt-in configuration for the new motion-control runtime."""

    enabled: EnabledField = False
    control_frequency_hz: Annotated[
        float,
        Field(
            title="Control frequency",
            description="Frequency of the motion arbiter and hardware watchdog.",
            ge=5,
            le=100,
        ),
    ] = 20.0
    command_timeout_ms: Annotated[
        int,
        Field(
            title="Command timeout",
            description=(
                "Maximum lifetime of a continuously refreshed manual or autonomous "
                "motion command."
            ),
            ge=200,
            le=2000,
        ),
    ] = 250
    max_forward_speed_mps: Annotated[
        Optional[float],
        Field(
            title="Measured maximum forward speed",
            description=(
                "Calibrated vehicle speed in metres per second at the configured "
                "maximum motor command. Required before enabling motion control."
            ),
            gt=0,
        ),
    ] = None
    max_reverse_speed_mps: Annotated[
        Optional[float],
        Field(
            title="Measured maximum reverse speed",
            description=(
                "Calibrated reverse speed magnitude in metres per second at the "
                "configured maximum motor command. Required before enabling motion "
                "control."
            ),
            gt=0,
        ),
    ] = None

    @model_validator(mode="after")
    def require_physical_calibration_when_enabled(self) -> Self:
        if self.enabled and (
            self.max_forward_speed_mps is None or self.max_reverse_speed_mps is None
        ):
            raise ValueError(
                "max forward and reverse speeds are required when motion control "
                "is enabled"
            )
        minimum_timeout_ms = 2_000 / self.control_frequency_hz
        if self.command_timeout_ms < minimum_timeout_ms:
            raise ValueError(
                "command timeout must cover at least two motion-control cycles"
            )
        return self


__all__ = ["MotionControlConfig"]
