"""Runtime diagnostics for localization sensor publishers."""

from typing import Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated


SensorName = Literal["lidar", "imu", "encoder"]


class SensorPublisherStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    sensor: SensorName
    enabled: bool
    running: bool
    published_messages: Annotated[int, Field(ge=0)] = 0
    last_timestamp_monotonic_ns: Optional[Annotated[int, Field(ge=0)]] = None
    error: Optional[str] = None


class LocalizationSensorStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    sensors: Tuple[SensorPublisherStatus, ...]


__all__ = [
    "LocalizationSensorStatus",
    "SensorName",
    "SensorPublisherStatus",
]
