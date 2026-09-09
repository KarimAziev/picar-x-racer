"""Versioned diagnostic recordings; playback never targets the live robot bus."""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class RecordingStatus(BaseModel):
    active: bool = False
    session_id: Optional[str] = None
    events_written: int = 0
    dropped_events: int = 0
    bytes_written: int = 0
    error: Optional[str] = None


class RecordingHeader(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["header"] = "header"
    format_version: Literal[1] = 1
    session_id: str
    created_utc: str
    config: Dict[str, Any]
    software: Dict[str, str]


class RecordingEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["event"] = "event"
    sequence: int = Field(ge=0)
    received_monotonic_ns: int = Field(ge=0)
    topic: str
    payload: Dict[str, Any]
    snapshot: bool = False


class RecordingFooter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["footer"] = "footer"
    events_written: int = Field(ge=0)
    dropped_events: int = Field(ge=0)
    error: Optional[str] = None
