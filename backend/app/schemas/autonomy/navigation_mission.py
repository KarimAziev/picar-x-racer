"""Operator contracts for reviewing and executing ordered navigation targets."""

from enum import Enum
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self

from app.schemas.autonomy.actions import ActionState
from app.schemas.autonomy.navigation_execution import NavigationExecutionStatus
from app.schemas.autonomy.navigation import (
    NavigationPlanState,
    NavigationPlanStatus,
    NavigationPoint,
)


class NavigationMissionMode(str, Enum):
    ONCE = "once"
    LOOP = "loop"


class NavigationMissionTarget(NavigationPoint):
    """One deliberate operator-selected stop in a mission."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dwell_seconds: float = Field(default=0.0, ge=0.0, le=60.0, allow_inf_nan=False)


class NavigationMissionReviewRequest(BaseModel):
    """Ordered targets and policy to validate without moving the vehicle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    targets: Tuple[NavigationMissionTarget, ...] = Field(min_length=1, max_length=32)
    mode: NavigationMissionMode = NavigationMissionMode.ONCE
    lap_count: int = Field(default=1, ge=1, le=100)
    clearance_m: float = Field(default=0.20, ge=0.0, le=1.0, allow_inf_nan=False)
    allow_unknown: bool = False

    @model_validator(mode="after")
    def validate_targets(self) -> Self:
        if self.mode == NavigationMissionMode.LOOP and len(self.targets) < 2:
            raise ValueError("a loop mission requires at least two targets")
        for index, target in enumerate(self.targets):
            for previous in self.targets[:index]:
                if (target.x_m - previous.x_m) ** 2 + (
                    target.y_m - previous.y_m
                ) ** 2 < 0.01**2:
                    raise ValueError("mission targets must be at least 0.01 m apart")
        return self


class NavigationMissionLeg(BaseModel):
    """One preflight-validated route between mission stops."""

    model_config = ConfigDict(frozen=True)

    from_target_index: Optional[int] = Field(default=None, ge=0)
    to_target_index: int = Field(ge=0)
    plan: NavigationPlanStatus


class NavigationMissionPlanStatus(BaseModel):
    """Complete non-driving preflight for an ordered target mission."""

    model_config = ConfigDict(frozen=True)

    available: bool
    state: NavigationPlanState = NavigationPlanState.IDLE
    frame_id: str = "odom"
    mode: NavigationMissionMode = NavigationMissionMode.ONCE
    lap_count: int = Field(default=1, ge=1)
    targets: Tuple[NavigationMissionTarget, ...] = ()
    legs: Tuple[NavigationMissionLeg, ...] = ()
    map_sequence: Optional[int] = Field(default=None, ge=0)
    total_path_length_m: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    total_reverse_distance_m: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    reason: Optional[str] = None

    @classmethod
    def idle(cls) -> "NavigationMissionPlanStatus":
        return cls(
            available=True,
            reason="Add map targets, then review the complete mission",
        )


class NavigationMissionExecutionRequest(BaseModel):
    """Conservative tracking parameters shared by every live mission leg."""

    model_config = ConfigDict(extra="forbid")

    max_speed_mps: float = Field(default=0.15, gt=0.0, le=0.5, allow_inf_nan=False)
    lookahead_m: float = Field(default=0.25, ge=0.10, le=1.0, allow_inf_nan=False)
    goal_tolerance_m: float = Field(default=0.08, ge=0.02, le=0.30, allow_inf_nan=False)
    leg_timeout_seconds: Optional[float] = Field(
        default=None, gt=0.0, le=300.0, allow_inf_nan=False
    )


class NavigationMissionExecutionStatus(BaseModel):
    """Progress and terminal state for a reviewed mission."""

    model_config = ConfigDict(frozen=True)

    available: bool
    state: ActionState = ActionState.IDLE
    mission_id: Optional[str] = None
    mode: NavigationMissionMode = NavigationMissionMode.ONCE
    current_lap: int = Field(default=0, ge=0)
    total_laps: int = Field(default=1, ge=1)
    active_target_index: Optional[int] = Field(default=None, ge=0)
    completed_target_visits: int = Field(default=0, ge=0)
    total_target_visits: int = Field(default=0, ge=0)
    map_sequence: Optional[int] = Field(default=None, ge=0)
    current_leg_path_length_m: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    completed_distance_m: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    reason: Optional[str] = None

    @classmethod
    def idle(cls) -> "NavigationMissionExecutionStatus":
        return cls(available=True, reason="Review a mission before starting it")

    @classmethod
    def unavailable(cls) -> "NavigationMissionExecutionStatus":
        return cls(
            available=False,
            reason=(
                "mission execution requires motion control, fused localization, "
                "and Ackermann geometry"
            ),
        )


class NavigationMissionRuntime(BaseModel):
    """One consistent snapshot of mission progress and the current live route."""

    model_config = ConfigDict(frozen=True)

    mission: NavigationMissionExecutionStatus
    execution: NavigationExecutionStatus
    route: NavigationPlanStatus


__all__ = [
    "NavigationMissionExecutionRequest",
    "NavigationMissionExecutionStatus",
    "NavigationMissionLeg",
    "NavigationMissionMode",
    "NavigationMissionPlanStatus",
    "NavigationMissionReviewRequest",
    "NavigationMissionTarget",
]
