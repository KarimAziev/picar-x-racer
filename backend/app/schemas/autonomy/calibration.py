"""Requests and reviewable measurements for guided robot calibration."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

CalibrationKind = Literal[
    "wheel_distance",
    "speed",
    "imu_bias",
    "steering_center",
    "steering_range",
    "stopping",
]


class CalibrationStart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: CalibrationKind
    direction: Literal["forward", "reverse"] = "forward"
    power_percent: int = Field(default=20, ge=5, le=100)
    stop_distance_m: float = Field(default=0.6, ge=0.2, le=5, allow_inf_nan=False)
    max_duration_s: float = Field(default=8, ge=2, le=15, allow_inf_nan=False)
    clear_path_confirmed: bool = False


class CalibrationHeartbeat(BaseModel):
    sequence: int = Field(ge=0)
    drive: bool = False
    steering_degrees: float = Field(default=0, ge=-45, le=45, allow_inf_nan=False)


class CalibrationFinish(BaseModel):
    measured_distance_m: float | None = Field(
        default=None, ge=0.2, le=10, allow_inf_nan=False
    )
    measured_wheel_angle_deg: float | None = Field(
        default=None, ge=-45, le=45, allow_inf_nan=False
    )


class CalibrationTrial(BaseModel):
    id: str
    kind: CalibrationKind
    accepted: bool
    reason: str
    direction: Literal["forward", "reverse"] = "forward"
    power_percent: int = 0
    duration_s: float = 0
    distance_m: float | None = None
    mean_speed_mps: float | None = None
    minimum_speed_mps: float | None = None
    maximum_speed_mps: float | None = None
    distance_per_tick_m: float | None = None
    gyro_bias_radps: float | None = None
    sensor_angle_deg: float | None = None
    steering_degrees: float | None = None
    stopping_distance_m: float | None = None
    config_fingerprint: str


class CalibrationApply(BaseModel):
    trial_ids: list[str] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique_trials(self) -> Self:
        if len(set(self.trial_ids)) != len(self.trial_ids):
            raise ValueError("Choose each calibration trial only once.")
        return self


class CalibrationStatus(BaseModel):
    active: bool = False
    max_power_percent: int = 20
    session_id: str | None = None
    kind: CalibrationKind | None = None
    driving: bool = False
    elapsed_s: float = 0
    encoder_ticks: float | None = None
    wall_distance_m: float | None = None
    gyro_radps: float | None = None
    sensor_angle_deg: float | None = None
    blockers: list[str] = Field(default_factory=list)
    trials: list[CalibrationTrial] = Field(default_factory=list)
    saved_config: dict[str, Any] | None = None
