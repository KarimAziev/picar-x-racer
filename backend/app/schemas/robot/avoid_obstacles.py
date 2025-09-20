from enum import Enum, auto
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AvoidState(Enum):
    CRUISE = auto()
    TURN = auto()
    REVERSE = auto()
    WAIT = auto()


class AvoidParams(BaseModel):
    """
    The configuration for the avoid obstacles mode.
    """

    safe: Annotated[
        float,
        Field(
            ge=0,
            description="Distance at or above this is fully comfortable to go straight.",
        ),
    ] = 80.0
    caution: Annotated[
        float,
        Field(ge=0, description="Below this, prefer turning or stop-turn behavior."),
    ] = 55.0
    danger: Annotated[
        float, Field(ge=0, description="Below this, prepare to reverse soon.")
    ] = 40.0
    stop: Annotated[
        float,
        Field(
            ge=0, description="Immediate stop/reverse if distance is at or below this."
        ),
    ] = 30.0

    forward_speed: Annotated[
        int, Field(ge=0, le=100, description="Target speed while cruising forward (%).")
    ] = 40
    turn_speed: Annotated[
        int, Field(ge=0, le=100, description="Target speed while turning (%).")
    ] = 40
    reverse_speed: Annotated[
        int, Field(ge=0, le=100, description="Target speed while reversing (%).")
    ] = 40

    turn_angle: Annotated[
        float,
        Field(ge=-45, le=45, description="Steering angle while turning forward (deg)."),
    ] = 30.0
    reverse_angle: Annotated[
        float,
        Field(
            ge=-45,
            le=45,
            description="Steering angle while reversing (deg). Can be negative.",
        ),
    ] = -30.0

    reverse_time_s: Annotated[
        float, Field(gt=0, description="Time to reverse before pausing (s).")
    ] = 0.9
    wait_time_s: Annotated[
        float,
        Field(
            ge=0, description="Pause after reversing before trying to turn again (s)."
        ),
    ] = 0.25
    loop_period_s: Annotated[
        float, Field(gt=0, description="Control loop period (s).")
    ] = 0.03
    hold_cruise_s: Annotated[
        float,
        Field(
            ge=0,
            description="Min time with safe distance before returning to CRUISE (s).",
        ),
    ] = 0.35
    stale_timeout_s: Annotated[
        float,
        Field(
            gt=0,
            description="If no valid distance for this long, treat sensor as stale and stop (s).",
        ),
    ] = 0.3

    accel_rate: Annotated[
        float, Field(gt=0, description="Max speed increase per second (%/s).")
    ] = 100.0
    decel_rate: Annotated[
        float, Field(gt=0, description="Max speed decrease per second (%/s).")
    ] = 500.0

    ema_alpha: Annotated[
        float,
        Field(
            ge=0,
            le=1,
            description="EMA smoothing factor for distance (0=no smoothing, 1=instant).",
        ),
    ] = 0.2
    max_range_cm: Annotated[
        float,
        Field(
            ge=0,
            description="Clamp upper bound for distance readings to ignore spikes (cm).",
        ),
    ] = 300.0

    model_config = ConfigDict(validate_assignment=True)

    @model_validator(mode="after")
    def _order_ok(self):
        if not (self.safe >= self.caution >= self.danger >= self.stop):
            raise ValueError("Distances must satisfy: safe ≥ caution ≥ danger ≥ stop")
        return self
