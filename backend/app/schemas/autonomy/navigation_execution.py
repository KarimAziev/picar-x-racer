"""Operator contracts for executing one reviewed navigation route."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.autonomy.actions import ActionState
from app.schemas.autonomy.navigation import NavigationDirection, NavigationPoint


class NavigationExecutionRequest(BaseModel):
    """Conservative pure-pursuit parameters for one navigation action."""

    model_config = ConfigDict(extra="forbid")

    max_speed_mps: float = Field(default=0.15, gt=0.0, le=0.5, allow_inf_nan=False)
    lookahead_m: float = Field(default=0.25, ge=0.10, le=1.0, allow_inf_nan=False)
    goal_tolerance_m: float = Field(default=0.08, ge=0.02, le=0.30, allow_inf_nan=False)
    timeout_seconds: Optional[float] = Field(
        default=None, gt=0.0, le=300.0, allow_inf_nan=False
    )


class NavigationExecutionStatus(BaseModel):
    """Progress and terminal state for the current navigation action."""

    model_config = ConfigDict(frozen=True)

    available: bool
    state: ActionState = ActionState.IDLE
    action_id: Optional[str] = None
    goal: Optional[NavigationPoint] = None
    current_pose: Optional[NavigationPoint] = None
    map_sequence: Optional[int] = Field(default=None, ge=0)
    path_length_m: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    progress_m: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    remaining_m: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    target_waypoint_index: Optional[int] = Field(default=None, ge=0)
    max_speed_mps: Optional[float] = Field(default=None, gt=0, allow_inf_nan=False)
    commanded_speed_mps: float = Field(default=0.0, allow_inf_nan=False)
    motion_direction: Optional[NavigationDirection] = None
    gear_changes_completed: int = Field(default=0, ge=0)
    gear_changes_total: int = Field(default=0, ge=0)
    steering_angle_deg: float = Field(default=0.0, allow_inf_nan=False)
    cross_track_error_m: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    reason: Optional[str] = None

    @classmethod
    def idle(cls) -> "NavigationExecutionStatus":
        return cls(available=True, reason="Select and review a navigation goal")

    @classmethod
    def unavailable(cls) -> "NavigationExecutionStatus":
        return cls(
            available=False,
            reason="navigation requires motion control, localization, and Ackermann geometry",
        )


__all__ = ["NavigationExecutionRequest", "NavigationExecutionStatus"]
