from enum import Enum, auto
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AvoidState(Enum):
    CRUISE = auto()
    TURN = auto()
    REVERSE = auto()
    WAIT = auto()


class AvoidParams(BaseModel):
    safe: Annotated[float, Field(..., ge=0)] = 80.0
    caution: Annotated[float, Field(..., ge=0)] = 55.0
    danger: Annotated[float, Field(..., ge=0)] = 40.0
    stop: Annotated[float, Field(..., ge=0)] = 30.0

    forward_speed: Annotated[int, Field(..., ge=0, le=100)] = 40
    turn_speed: Annotated[int, Field(..., ge=0, le=100)] = 40
    reverse_speed: Annotated[int, Field(..., ge=0, le=100)] = 40

    turn_angle: Annotated[float, Field(..., ge=-45, le=45)] = 30.0
    reverse_angle: Annotated[float, Field(..., ge=0, le=45)] = -30.0

    reverse_time_s: Annotated[float, Field(..., gt=0)] = 0.9
    wait_time_s: Annotated[float, Field(..., ge=0)] = 0.25
    loop_period_s: Annotated[float, Field(..., gt=0)] = 0.03
    hold_cruise_s: Annotated[float, Field(..., ge=0)] = 0.35
    stale_timeout_s: Annotated[float, Field(..., gt=0)] = 0.3

    accel_rate: Annotated[float, Field(..., gt=0)] = 100.0
    decel_rate: Annotated[float, Field(..., gt=0)] = 500.0

    ema_alpha: Annotated[float, Field(..., ge=0, le=1)] = 0.2
    max_range_cm: Annotated[float, Field(..., ge=0, le=1)] = 300.0

    model_config = ConfigDict(validate_assignment=True)

    @model_validator(mode="after")
    def _order_ok(self):
        if not (self.safe >= self.caution >= self.danger >= self.stop):
            raise ValueError("Distances must satisfy: safe ≥ caution ≥ danger ≥ stop")
        return self
