"""Framed, monotonic messages for sensors and robot state."""

import math
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Annotated, Self


FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
PositiveFiniteFloat = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class FrozenMessage(BaseModel):
    model_config = ConfigDict(frozen=True)


class MessageHeader(FrozenMessage):
    """Identity, frame, and process-local monotonic observation time."""

    sequence: Annotated[int, Field(ge=0)]
    frame_id: str
    timestamp_monotonic_ns: Annotated[int, Field(ge=0)]
    source_timestamp_ns: Optional[Annotated[int, Field(ge=0)]] = None

    @field_validator("frame_id")
    @classmethod
    def validate_frame_id(cls, value: str) -> str:
        frame_id = value.strip()
        if not frame_id:
            raise ValueError("frame_id must not be empty")
        if frame_id.startswith("/"):
            raise ValueError("frame_id must not start with a slash")
        return frame_id


class LaserScan(FrozenMessage):
    """One planar range scan in radians and metres."""

    header: MessageHeader
    angle_min_rad: FiniteFloat
    angle_max_rad: FiniteFloat
    angle_increment_rad: PositiveFiniteFloat
    range_min_m: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    range_max_m: PositiveFiniteFloat
    ranges_m: Tuple[float, ...]
    intensities: Optional[Tuple[FiniteFloat, ...]] = None

    @field_validator("ranges_m")
    @classmethod
    def validate_ranges(cls, values: Tuple[float, ...]) -> Tuple[float, ...]:
        if not values:
            raise ValueError("ranges_m must not be empty")
        for value in values:
            if math.isnan(value) or value < 0:
                raise ValueError("ranges_m values must be non-negative or infinity")
        return values

    @model_validator(mode="after")
    def validate_scan_shape(self) -> Self:
        if self.angle_max_rad < self.angle_min_rad:
            raise ValueError("angle_max_rad must not be less than angle_min_rad")
        if self.range_max_m <= self.range_min_m:
            raise ValueError("range_max_m must be greater than range_min_m")
        if self.intensities is not None and len(self.intensities) != len(self.ranges_m):
            raise ValueError("intensities and ranges_m must have equal lengths")
        return self


class ImuData(FrozenMessage):
    """Minimal planar-navigation IMU observation in SI units."""

    header: MessageHeader
    angular_velocity_z_radps: FiniteFloat
    acceleration_x_mps2: FiniteFloat
    acceleration_y_mps2: FiniteFloat
    acceleration_z_mps2: FiniteFloat
    yaw_rad: Optional[FiniteFloat] = None


class EncoderState(FrozenMessage):
    """Signed cumulative and incremental drive-encoder state."""

    header: MessageHeader
    ticks: int
    delta_ticks: int


class SteeringState(FrozenMessage):
    """Commanded steering plus optional measured wheel angle."""

    header: MessageHeader
    commanded_angle_rad: FiniteFloat
    measured_angle_rad: Optional[FiniteFloat] = None


class Odometry2D(FrozenMessage):
    """Planar odometry pose and twist, normally odom -> base_link."""

    header: MessageHeader
    child_frame_id: str = "base_link"
    x_m: FiniteFloat
    y_m: FiniteFloat
    yaw_rad: FiniteFloat
    linear_speed_mps: FiniteFloat
    yaw_rate_radps: FiniteFloat

    @field_validator("child_frame_id")
    @classmethod
    def validate_child_frame_id(cls, value: str) -> str:
        frame_id = value.strip()
        if not frame_id or frame_id.startswith("/"):
            raise ValueError("child_frame_id must be non-empty and relative")
        return frame_id


__all__ = [
    "EncoderState",
    "ImuData",
    "LaserScan",
    "MessageHeader",
    "Odometry2D",
    "SteeringState",
]
