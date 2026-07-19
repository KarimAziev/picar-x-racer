"""Opt-in hardware acquisition settings for localization sensors."""

from typing import Literal, Optional

from app.schemas.robot.common import AddressField, EnabledField, IC2Bus
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Annotated, Self


FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]


def _validate_frame_id(value: str) -> str:
    frame_id = value.strip()
    if not frame_id or frame_id.startswith("/"):
        raise ValueError("frame_id must be non-empty and relative")
    return frame_id


class StaticTransformConfig(BaseModel):
    """Measured transform from ``base_link`` to a sensor frame."""

    x_m: FiniteFloat = 0.0
    y_m: FiniteFloat = 0.0
    z_m: FiniteFloat = 0.0
    roll_rad: FiniteFloat = 0.0
    pitch_rad: FiniteFloat = 0.0
    yaw_rad: FiniteFloat = 0.0


class RPLidarC1SensorConfig(BaseModel):
    enabled: EnabledField = False
    driver: Literal["rplidar_c1"] = "rplidar_c1"
    port: Annotated[
        str,
        Field(
            title="Serial port",
            description="Prefer a stable /dev/serial/by-id path when available.",
            min_length=1,
        ),
    ] = "/dev/ttyUSB0"
    baudrate: Annotated[int, Field(gt=0)] = 460800
    timeout_s: Annotated[float, Field(gt=0, le=10, allow_inf_nan=False)] = 1.0
    frame_id: str = "laser"
    transform: StaticTransformConfig = Field(default_factory=StaticTransformConfig)
    range_min_m: Annotated[Optional[float], Field(ge=0, allow_inf_nan=False)] = None
    range_max_m: Annotated[Optional[float], Field(gt=0, allow_inf_nan=False)] = None
    angular_resolution_deg: Annotated[
        float, Field(gt=0, le=45, allow_inf_nan=False)
    ] = 1.0
    min_measurements_per_scan: Annotated[int, Field(ge=1, le=10_000)] = 50

    @field_validator("frame_id")
    @classmethod
    def validate_frame_id(cls, value: str) -> str:
        return _validate_frame_id(value)

    @model_validator(mode="after")
    def require_ranges_when_enabled(self) -> Self:
        if self.enabled and (self.range_min_m is None or self.range_max_m is None):
            raise ValueError(
                "lidar range_min_m and range_max_m are required when enabled"
            )
        if (
            self.range_min_m is not None
            and self.range_max_m is not None
            and self.range_max_m <= self.range_min_m
        ):
            raise ValueError("lidar range_max_m must be greater than range_min_m")
        return self


class SH3001SensorConfig(BaseModel):
    enabled: EnabledField = False
    driver: Literal["sh3001"] = "sh3001"
    bus: IC2Bus = 1
    address: AddressField = "0x36"
    frame_id: str = "imu"
    transform: StaticTransformConfig = Field(default_factory=StaticTransformConfig)
    sample_frequency_hz: Annotated[float, Field(ge=1, le=500, allow_inf_nan=False)] = (
        100.0
    )
    accelerometer_range_g: Literal[2, 4, 8, 16] = 2
    gyroscope_range_dps: Literal[125, 250, 500, 1000, 2000] = 2000

    @field_validator("address", mode="before")
    @classmethod
    def validate_address(cls, value: AddressField) -> AddressField:
        if isinstance(value, str):
            try:
                parsed = int(value, 16)
            except ValueError as error:
                raise ValueError(
                    "IMU address must be an integer or hexadecimal"
                ) from error
        else:
            parsed = value
        if parsed < 0 or parsed > 0x7F:
            raise ValueError("IMU address must be in the range 0x00 through 0x7F")
        return value

    @field_validator("frame_id")
    @classmethod
    def validate_frame_id(cls, value: str) -> str:
        return _validate_frame_id(value)

    @property
    def address_int(self) -> int:
        return self.address if isinstance(self.address, int) else int(self.address, 16)


class EncoderSensorConfig(BaseModel):
    enabled: EnabledField = False
    driver: Literal["external"] = "external"
    frame_id: str = "encoder"
    sample_frequency_hz: Annotated[float, Field(ge=1, le=1000, allow_inf_nan=False)] = (
        100.0
    )

    @field_validator("frame_id")
    @classmethod
    def validate_frame_id(cls, value: str) -> str:
        return _validate_frame_id(value)


class LocalizationSensorsConfig(BaseModel):
    lidar: RPLidarC1SensorConfig = Field(default_factory=RPLidarC1SensorConfig)
    imu: SH3001SensorConfig = Field(default_factory=SH3001SensorConfig)
    encoder: EncoderSensorConfig = Field(default_factory=EncoderSensorConfig)


__all__ = [
    "EncoderSensorConfig",
    "LocalizationSensorsConfig",
    "RPLidarC1SensorConfig",
    "SH3001SensorConfig",
    "StaticTransformConfig",
]
