from enum import Enum, auto
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self


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
            title="Safe distance",
            ge=0,
            description=(
                "Distance in centimetres at or above which the robot can cruise "
                "straight ahead."
            ),
        ),
    ] = 80.0
    caution: Annotated[
        float,
        Field(
            title="Caution distance",
            ge=0,
            description=(
                "Distance in centimetres below which the robot prefers turning or "
                "stop-and-turn behavior."
            ),
        ),
    ] = 55.0
    danger: Annotated[
        float,
        Field(
            title="Danger distance",
            ge=0,
            description="Distance in centimetres below which reversal is prepared.",
        ),
    ] = 40.0
    stop: Annotated[
        float,
        Field(
            title="Stop distance",
            ge=0,
            description=(
                "Distance in centimetres at or below which the robot immediately "
                "stops and reverses."
            ),
        ),
    ] = 30.0

    forward_speed: Annotated[
        int,
        Field(
            title="Forward speed",
            ge=0,
            le=100,
            description="Target forward cruising speed as a percentage.",
        ),
    ] = 40
    turn_speed: Annotated[
        int,
        Field(
            title="Turn speed",
            ge=0,
            le=100,
            description="Target forward speed while turning, as a percentage.",
        ),
    ] = 40
    reverse_speed: Annotated[
        int,
        Field(
            title="Reverse speed",
            ge=0,
            le=100,
            description="Target reversing speed as a percentage.",
        ),
    ] = 40

    turn_angle: Annotated[
        float,
        Field(
            title="Forward turn angle",
            ge=-45,
            le=45,
            description="Steering angle in degrees while turning forward.",
        ),
    ] = 30.0
    reverse_angle: Annotated[
        float,
        Field(
            title="Reverse turn angle",
            ge=-45,
            le=45,
            description="Steering angle in degrees while reversing; may be negative.",
        ),
    ] = -30.0

    reverse_time_s: Annotated[
        float,
        Field(
            title="Reverse duration",
            gt=0,
            description="Time in seconds to reverse before pausing.",
        ),
    ] = 0.9
    wait_time_s: Annotated[
        float,
        Field(
            title="Wait duration",
            ge=0,
            description=(
                "Pause in seconds after reversing before trying to turn again."
            ),
        ),
    ] = 0.25
    loop_period_s: Annotated[
        float,
        Field(
            title="Control-loop period",
            gt=0,
            description="Time in seconds between obstacle-control updates.",
        ),
    ] = 0.03
    hold_cruise_s: Annotated[
        float,
        Field(
            title="Cruise hold duration",
            ge=0,
            description=(
                "Minimum time in seconds with a safe distance before returning to "
                "cruise."
            ),
        ),
    ] = 0.35
    stale_timeout_s: Annotated[
        float,
        Field(
            title="Sensor stale timeout",
            gt=0,
            description=(
                "Stop when no valid distance measurement arrives within this many "
                "seconds."
            ),
        ),
    ] = 0.3

    accel_rate: Annotated[
        float,
        Field(
            title="Acceleration rate",
            gt=0,
            description="Maximum speed-command increase in percentage points per second.",
        ),
    ] = 100.0
    decel_rate: Annotated[
        float,
        Field(
            title="Deceleration rate",
            gt=0,
            description="Maximum speed-command decrease in percentage points per second.",
        ),
    ] = 500.0

    ema_alpha: Annotated[
        float,
        Field(
            title="Distance smoothing",
            ge=0,
            le=1,
            description=(
                "Exponential moving-average factor for distance; zero keeps the "
                "previous value and one uses the latest value immediately."
            ),
        ),
    ] = 0.2
    max_range_cm: Annotated[
        float,
        Field(
            title="Maximum distance",
            ge=0,
            description=(
                "Upper bound in centimetres used to clamp distance readings and "
                "ignore spikes."
            ),
        ),
    ] = 300.0

    model_config = ConfigDict(validate_assignment=True)

    @model_validator(mode="after")
    def _order_ok(self) -> Self:
        if not (self.safe >= self.caution >= self.danger >= self.stop):
            raise ValueError("Distances must satisfy: safe ≥ caution ≥ danger ≥ stop")
        return self
