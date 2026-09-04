"""Operator-facing contracts for planning a map-relative navigation goal."""

from enum import Enum
from typing import Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Self


class NavigationPlanState(str, Enum):
    IDLE = "idle"
    READY = "ready"
    REJECTED = "rejected"
    FAILED = "failed"


class NavigationDirection(str, Enum):
    FORWARD = "forward"
    REVERSE = "reverse"


class NavigationPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    x_m: float = Field(allow_inf_nan=False)
    y_m: float = Field(allow_inf_nan=False)


class NavigationGoalRequest(NavigationPoint):
    model_config = ConfigDict(extra="forbid", frozen=True)

    clearance_m: float = Field(default=0.20, ge=0.0, le=1.0, allow_inf_nan=False)
    allow_unknown: bool = False


class NavigationPlanStatus(BaseModel):
    """A non-driving route preview computed from one occupancy-map snapshot."""

    model_config = ConfigDict(frozen=True)

    available: bool
    state: NavigationPlanState = NavigationPlanState.IDLE
    frame_id: str = "odom"
    goal: Optional[NavigationPoint] = None
    start: Optional[NavigationPoint] = None
    path: Tuple[NavigationPoint, ...] = ()
    path_directions: Tuple[NavigationDirection, ...] = ()
    path_length_m: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    reverse_distance_m: float = Field(default=0.0, ge=0.0, allow_inf_nan=False)
    gear_changes: int = Field(default=0, ge=0)
    clearance_m: float = Field(default=0.20, ge=0.0, allow_inf_nan=False)
    allow_unknown: bool = False
    map_sequence: Optional[int] = Field(default=None, ge=0)
    pose_source: Optional[Literal["localization", "odometry"]] = None
    start_yaw_rad: Optional[float] = Field(default=None, allow_inf_nan=False)
    expanded_nodes: int = Field(default=0, ge=0)
    planning_method: Literal["grid_astar", "hybrid_astar"] = "grid_astar"
    geometry_validated: bool = False
    smoothed: bool = False
    raw_waypoint_count: int = Field(default=0, ge=0)
    max_curvature_per_m: Optional[float] = Field(
        default=None, ge=0.0, allow_inf_nan=False
    )
    curvature_limit_per_m: Optional[float] = Field(
        default=None, gt=0.0, allow_inf_nan=False
    )
    minimum_turning_radius_m: Optional[float] = Field(
        default=None, gt=0.0, allow_inf_nan=False
    )
    initial_heading_error_deg: Optional[float] = Field(
        default=None, ge=-180.0, le=180.0, allow_inf_nan=False
    )
    reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_route_metadata(self) -> Self:
        if self.path_directions and len(self.path_directions) != len(self.path) - 1:
            raise ValueError("path_directions must describe every path segment")
        if self.reverse_distance_m > self.path_length_m + 1e-9:
            raise ValueError("reverse distance cannot exceed total path length")
        if self.gear_changes > max(0, len(self.path) - 2):
            raise ValueError("gear changes cannot exceed path junctions")
        return self

    @classmethod
    def idle(cls) -> "NavigationPlanStatus":
        return cls(
            available=True,
            reason="Click a free map location to preview a route",
        )


__all__ = [
    "NavigationDirection",
    "NavigationGoalRequest",
    "NavigationPlanState",
    "NavigationPlanStatus",
    "NavigationPoint",
]
