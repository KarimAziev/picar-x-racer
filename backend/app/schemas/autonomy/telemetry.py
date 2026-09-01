"""JSON-safe, rate-limited telemetry contracts for external observers."""

import math
from typing import Literal, Optional, Tuple, Union

from app.schemas.autonomy.messages import (
    EncoderState,
    ImuData,
    MessageHeader,
    Odometry2D,
    SafetyState,
    SimulationState,
)
from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated


TelemetryChannel = Literal[
    "lidar",
    "imu",
    "encoder",
    "odometry",
    "safety",
    "simulation",
]
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
PositiveFiniteFloat = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class LaserScanTelemetry(BaseModel):
    """A JSON-safe laser scan where missing returns are represented by null."""

    model_config = ConfigDict(frozen=True)

    header: MessageHeader
    angle_min_rad: FiniteFloat
    angle_max_rad: FiniteFloat
    angle_increment_rad: PositiveFiniteFloat
    range_min_m: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    range_max_m: PositiveFiniteFloat
    ranges_m: Tuple[Optional[FiniteFloat], ...]
    intensities: Optional[Tuple[FiniteFloat, ...]] = None


TelemetryPayload = Union[
    LaserScanTelemetry,
    ImuData,
    EncoderState,
    Odometry2D,
    SafetyState,
    SimulationState,
]


class TelemetryEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True)

    channel: TelemetryChannel
    topic: str
    payload: TelemetryPayload


def json_safe_ranges(values: Tuple[float, ...]) -> Tuple[Optional[float], ...]:
    """Translate the LaserScan infinity sentinel into standard JSON nulls."""

    return tuple(value if math.isfinite(value) else None for value in values)


__all__ = [
    "LaserScanTelemetry",
    "TelemetryChannel",
    "TelemetryEnvelope",
    "TelemetryPayload",
    "json_safe_ranges",
]
