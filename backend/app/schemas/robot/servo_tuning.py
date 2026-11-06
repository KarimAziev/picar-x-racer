from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ServoName = Literal["steering_servo", "cam_pan_servo", "cam_tilt_servo"]


class ServoTuningSettings(BaseModel):
    """Runtime-adjustable servo geometry; wiring remains in hardware settings."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    reverse: Optional[bool] = Field(default=None, strict=True)
    min_angle: Optional[int] = Field(default=None, ge=-360, le=360)
    max_angle: Optional[int] = Field(default=None, ge=-360, le=360)
    dec_step: Optional[int] = Field(default=None, lt=0)
    inc_step: Optional[int] = Field(default=None, gt=0)
    min_pulse: Optional[int] = Field(default=None, ge=20)
    max_pulse: Optional[int] = Field(default=None, le=3000)
    real_min_angle: Optional[float] = Field(default=None, ge=-360, le=360)
    real_max_angle: Optional[float] = Field(default=None, ge=-360, le=360)


class ServoTuningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    servo: ServoName
    settings: ServoTuningSettings
    angle: float = Field(ge=-360, le=360)
