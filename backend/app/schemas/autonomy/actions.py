"""Operator-facing contracts for bounded autonomous actions."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ActionState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"
    CANCELED = "canceled"


class RelativeActionType(str, Enum):
    DISTANCE = "distance"
    ARC = "arc"


class RelativeDistanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distance_m: float = Field(ge=-10.0, le=10.0)
    speed_mps: float = Field(default=0.15, gt=0.0, le=1.0)
    timeout_seconds: Optional[float] = Field(default=None, gt=0.0, le=120.0)

    @model_validator(mode="after")
    def validate_nonzero_distance(self) -> "RelativeDistanceRequest":
        if abs(self.distance_m) < 0.01:
            raise ValueError("distance_m magnitude must be at least 0.01 m")
        return self


class RelativeArcRequest(RelativeDistanceRequest):
    steering_angle_deg: float = Field(ge=-60.0, le=60.0)

    @model_validator(mode="after")
    def validate_nonzero_steering(self) -> "RelativeArcRequest":
        if abs(self.steering_angle_deg) < 1.0:
            raise ValueError("steering_angle_deg magnitude must be at least 1 degree")
        return self


class RelativeMotionStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    available: bool
    state: ActionState = ActionState.IDLE
    action_id: Optional[str] = None
    action_type: Optional[RelativeActionType] = None
    distance_m: Optional[float] = None
    requested_speed_mps: Optional[float] = None
    progress_m: float = 0.0
    remaining_m: Optional[float] = None
    steering_angle_deg: Optional[float] = None
    max_abs_steering_angle_deg: Optional[float] = None
    target_yaw_rad: Optional[float] = None
    yaw_progress_rad: Optional[float] = None
    reason: Optional[str] = None

    @classmethod
    def unavailable(cls) -> "RelativeMotionStatus":
        return cls(available=False, reason="relative motion is not configured")


__all__ = [
    "ActionState",
    "RelativeActionType",
    "RelativeArcRequest",
    "RelativeDistanceRequest",
    "RelativeMotionStatus",
]
