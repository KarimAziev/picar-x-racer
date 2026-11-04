"""Configuration needed to safely translate and execute physical motion."""

from typing import Optional

from app.schemas.robot.common import EnabledField
from app.schemas.robot.speed_calibration import (
    SpeedCalibrationPoint,
    validate_speed_curve,
)
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated, Self


class MotionControlConfig(BaseModel):
    """Opt-in configuration for the new motion-control runtime."""

    enabled: EnabledField = Field(
        default=False,
        description="Use measured speeds to control driving and provide steering angles for odometry. Fill in both maximum speeds before enabling. Save and restart the backend to apply changes.",
    )
    control_frequency_hz: Annotated[
        float,
        Field(
            title="Control frequency (Hz)",
            description="How often speed and steering commands are checked each second. 20 Hz means once every 50 ms. Higher rates use more processing.",
            ge=5,
            le=100,
        ),
    ] = 20.0
    command_timeout_ms: Annotated[
        int,
        Field(
            title="Command timeout (ms)",
            description=(
                "Stop the robot if no renewed driving command arrives within this time. 250 ms is a quarter of a second; increasing it lets the robot continue longer after a lost connection."
            ),
            ge=200,
            le=2000,
        ),
    ] = 250
    max_forward_speed_mps: Annotated[
        Optional[float],
        Field(
            title="Measured maximum forward speed (m/s)",
            description=(
                "Use Guided calibration > Driving speed to measure forward travel at several power levels. The guide saves the highest measured speed here, in metres per second. Driving requests are limited to this speed."
            ),
            gt=0,
        ),
    ] = None
    max_reverse_speed_mps: Annotated[
        Optional[float],
        Field(
            title="Measured maximum reverse speed (m/s)",
            description=(
                "Use Guided calibration > Driving speed to measure reverse travel separately. The guide saves a positive speed here, in metres per second, and limits reverse requests to it."
            ),
            gt=0,
        ),
    ] = None

    forward_speed_curve: list[SpeedCalibrationPoint] = Field(
        default_factory=list,
        title="Forward speed calibration",
        description="Measured by Guided calibration. Requests above the highest measured speed are limited to that speed.",
    )
    reverse_speed_curve: list[SpeedCalibrationPoint] = Field(
        default_factory=list,
        title="Reverse speed calibration",
        description="Measured by Guided calibration, separately from forward driving.",
    )

    @model_validator(mode="after")
    def require_physical_calibration_when_enabled(self) -> Self:
        if self.enabled and (
            self.max_forward_speed_mps is None or self.max_reverse_speed_mps is None
        ):
            raise ValueError(
                "Before enabling Motion control, enter Measured maximum forward speed (m/s) "
                "and Measured maximum reverse speed (m/s)."
            )
        for curve, limit in (
            (self.forward_speed_curve, self.max_forward_speed_mps),
            (self.reverse_speed_curve, self.max_reverse_speed_mps),
        ):
            validate_speed_curve(curve)
            if curve and (limit is None or abs(curve[-1].speed_mps - limit) > 1e-6):
                raise ValueError(
                    "The speed limit must match the highest measured point in its speed calibration curve."
                )
        minimum_timeout_ms = 2_000 / self.control_frequency_hz
        if self.command_timeout_ms < minimum_timeout_ms:
            raise ValueError(
                f"Increase Command timeout (ms) to at least {minimum_timeout_ms:g} ms "
                "or increase Control frequency (Hz), so the timeout covers two updates."
            )
        return self


__all__ = ["MotionControlConfig"]
