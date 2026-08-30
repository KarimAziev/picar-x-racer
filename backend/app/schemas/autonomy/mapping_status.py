"""Runtime state and diagnostics for local mapping sessions."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated


class MappingSessionState(str, Enum):
    DISABLED = "disabled"
    IDLE = "idle"
    ACTIVE = "active"
    PAUSED = "paused"


class MappingSessionStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    enabled: bool
    state: MappingSessionState
    session_id: Annotated[int, Field(ge=0)] = 0
    map_sequence: Annotated[int, Field(ge=0)] = 0
    scans_received: Annotated[int, Field(ge=0)] = 0
    scans_inserted: Annotated[int, Field(ge=0)] = 0
    returns_inserted: Annotated[int, Field(ge=0)] = 0
    ignored_inactive_scans: Annotated[int, Field(ge=0)] = 0
    rejected_missing_odometry: Annotated[int, Field(ge=0)] = 0
    rejected_stale_odometry: Annotated[int, Field(ge=0)] = 0
    has_map: bool = False

    @classmethod
    def disabled(cls) -> "MappingSessionStatus":
        return cls(enabled=False, state=MappingSessionState.DISABLED)


__all__ = ["MappingSessionState", "MappingSessionStatus"]
