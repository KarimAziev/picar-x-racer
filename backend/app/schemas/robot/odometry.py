"""Measured Ackermann geometry and encoder calibration."""

from typing import Optional

from app.schemas.robot.common import EnabledField
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Annotated, Self


class AckermannOdometryConfig(BaseModel):
    """Drive-encoder odometry using measured Ackermann vehicle geometry."""

    enabled: EnabledField = Field(
        default=False,
        description="Track movement from wheel turns and steering angle. First enable Motion control and Drive encoders under Localization sensors, then fill in the wheel measurements. Restart the backend after enabling.",
    )
    wheelbase_m: Annotated[
        Optional[float],
        Field(
            title="Wheelbase (m)",
            description="Measure between the centers of the front and rear axles. Enter metres: 25 cm = 0.25 m. Used to calculate how tightly the robot turns.",
            gt=0,
        ),
    ] = None
    wheel_radius_m: Annotated[
        Optional[float],
        Field(
            title="Driven wheel radius (m)",
            description="Distance from the center of a driven wheel to the floor with the robot resting on its wheels. Enter metres: 3 cm = 0.03 m. Used to convert wheel turns into distance.",
            gt=0,
        ),
    ] = None
    encoder_ticks_per_revolution: Annotated[
        Optional[int],
        Field(
            title="Encoder ticks per revolution",
            description="Counts reported for one complete turn of the encoder shaft. Use 16384 for AS5048A or 4096 for AS5600L. For GPIO encoders, include the selected x1, x2, or x4 counting mode.",
            gt=0,
        ),
    ] = None
    gear_ratio: Annotated[
        float,
        Field(
            title="Encoder-to-wheel gear ratio",
            description="Number of encoder shaft turns for one wheel turn. Use 1 if the encoder turns with the wheel; use 3 if it turns three times per wheel turn.",
            gt=0,
        ),
    ] = 1.0
    max_steering_age_ms: Annotated[
        int,
        Field(
            title="Steering update timeout (ms)",
            description="Stop updating the wheel-based position if the steering angle is older than this limit. 250 ms is a quarter of a second. Keep the default unless steering updates arrive too slowly.",
            ge=50,
            le=2000,
        ),
    ] = 250

    @model_validator(mode="after")
    def require_geometry_when_enabled(self) -> Self:
        required = {
            "Wheelbase (m)": self.wheelbase_m,
            "Driven wheel radius (m)": self.wheel_radius_m,
            "Encoder ticks per revolution": self.encoder_ticks_per_revolution,
        }
        missing = [name for name, value in required.items() if value is None]
        if self.enabled and missing:
            raise ValueError(
                "Before enabling Ackermann odometry, enter: " + ", ".join(missing)
            )
        return self


__all__ = ["AckermannOdometryConfig"]
