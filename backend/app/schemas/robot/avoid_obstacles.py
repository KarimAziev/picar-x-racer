from enum import Enum, auto
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AvoidState(Enum):
    CRUISE = auto()
    TURN = auto()
    REVERSE = auto()
    WAIT = auto()


class AvoidParams(BaseModel):
    safe: Annotated[float, Field(60.0, ge=0)] = 60.0
    caution: Annotated[float, Field(35.0, ge=0)] = 35.0
    danger: Annotated[float, Field(22.0, ge=0)] = 22.0
    stop: Annotated[float, Field(15.0, ge=0)] = 15.0

    forward_speed: Annotated[int, Field(50, ge=0, le=100)] = 50
    turn_speed: Annotated[int, Field(40, ge=0, le=100)] = 40
    reverse_speed: Annotated[int, Field(45, ge=0, le=100)] = 45

    turn_angle: Annotated[float, Field(35.0, ge=-45, le=45)] = 35.0
    reverse_angle: Annotated[float, Field(30.0, ge=0, le=45)] = 30.0

    reverse_time_s: Annotated[float, Field(0.7, gt=0)] = 0.7
    wait_time_s: Annotated[float, Field(0.25, ge=0)] = 0.25
    loop_period_s: Annotated[float, Field(0.05, gt=0)] = 0.05
    hold_cruise_s: Annotated[float, Field(0.25, ge=0)] = 0.25
    stale_timeout_s: Annotated[float, Field(0.5, gt=0)] = 0.5

    accel_rate: Annotated[float, Field(120.0, gt=0)] = 120.0
    decel_rate: Annotated[float, Field(200.0, gt=0)] = 200.0

    ema_alpha: Annotated[float, Field(0.35, ge=0, le=1)] = 0.35
    max_range_cm: float = 300.0

    model_config = ConfigDict(validate_assignment=True)

    @model_validator(mode="after")
    def _order_ok(self):
        if not (self.safe >= self.caution >= self.danger >= self.stop):
            raise ValueError("Distances must satisfy: safe ≥ caution ≥ danger ≥ stop")
        return self
