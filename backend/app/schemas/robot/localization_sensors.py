"""Opt-in real and simulated localization-sensor settings."""

from typing import List, Literal, Optional, Tuple, Union

from app.schemas.robot.common import AddressField, EnabledField, IC2Bus
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import Annotated, Self


FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
Vector3 = Tuple[FiniteFloat, FiniteFloat, FiniteFloat]
GPIOPin = Union[
    Annotated[int, Field(ge=0)],
    Annotated[str, Field(min_length=1)],
]


def _validate_frame_id(value: str) -> str:
    frame_id = value.strip()
    if not frame_id or frame_id.startswith("/"):
        raise ValueError("frame_id must be non-empty and relative")
    return frame_id


def _gpio_pin_key(value: int | str) -> str:
    if isinstance(value, int):
        return f"gpio{value}"
    normalized = value.strip().casefold()
    for prefix in ("gpio", "bcm"):
        suffix = normalized.removeprefix(prefix)
        if suffix.isdigit():
            return f"gpio{int(suffix)}"
    if normalized.isdigit():
        return f"gpio{int(normalized)}"
    return normalized


class StaticTransformConfig(BaseModel):
    """Measured transform from ``base_link`` to a sensor frame."""

    x_m: FiniteFloat = 0.0
    y_m: FiniteFloat = 0.0
    z_m: FiniteFloat = 0.0
    roll_rad: FiniteFloat = 0.0
    pitch_rad: FiniteFloat = 0.0
    yaw_rad: FiniteFloat = 0.0


class LidarSensorConfigBase(BaseModel):
    enabled: EnabledField = False
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


class RPLidarC1SensorConfig(LidarSensorConfigBase):
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


class MockLidarSensorConfig(LidarSensorConfigBase):
    """Uniform circular scan for mapping, safety, and telemetry development."""

    driver: Literal["mock"] = "mock"
    range_min_m: Annotated[Optional[float], Field(ge=0, allow_inf_nan=False)] = 0.05
    range_max_m: Annotated[Optional[float], Field(gt=0, allow_inf_nan=False)] = 12.0
    points_per_scan: Annotated[int, Field(ge=8, le=1440)] = 360
    distance_m: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 2.0
    quality: Annotated[int, Field(ge=0, le=255)] = 100
    scan_frequency_hz: Annotated[float, Field(gt=0, le=30, allow_inf_nan=False)] = 10.0
    min_measurements_per_scan: Annotated[int, Field(ge=1, le=10_000)] = 50


LidarSensorConfig = Annotated[
    Union[RPLidarC1SensorConfig, MockLidarSensorConfig],
    Field(discriminator="driver"),
]


class IMUSensorConfigBase(BaseModel):
    enabled: EnabledField = False
    frame_id: str = "imu"
    transform: StaticTransformConfig = Field(default_factory=StaticTransformConfig)
    sample_frequency_hz: Annotated[float, Field(ge=1, le=500, allow_inf_nan=False)] = (
        100.0
    )

    @field_validator("frame_id")
    @classmethod
    def validate_frame_id(cls, value: str) -> str:
        return _validate_frame_id(value)


class SH3001SensorConfig(IMUSensorConfigBase):
    driver: Literal["sh3001"] = "sh3001"
    bus: IC2Bus = 1
    address: AddressField = "0x36"
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

    @property
    def address_int(self) -> int:
        return self.address if isinstance(self.address, int) else int(self.address, 16)


class MockIMUSensorConfig(IMUSensorConfigBase):
    driver: Literal["mock"] = "mock"
    acceleration_mps2: Vector3 = (0.0, 0.0, 9.80665)
    angular_velocity_radps: Vector3 = (0.0, 0.0, 0.0)


IMUSensorConfig = Annotated[
    Union[SH3001SensorConfig, MockIMUSensorConfig],
    Field(discriminator="driver"),
]


class DriveEncoderConfigBase(BaseModel):
    side: Literal["left", "right"]
    invert_direction: bool = False


class AS5048AEncoderConfig(DriveEncoderConfigBase):
    driver: Literal["as5048a"] = "as5048a"
    bus: Annotated[int, Field(ge=0)] = 0
    device: Annotated[int, Field(ge=0)] = 0
    max_speed_hz: Annotated[int, Field(gt=0, le=10_000_000)] = 1_000_000
    max_sample_gap_ms: Annotated[Optional[int], Field(gt=0, le=10_000)] = 100
    max_abs_speed_rps: Annotated[Optional[float], Field(gt=0, allow_inf_nan=False)] = (
        5.0
    )

    @property
    def max_sample_gap_ns(self) -> Optional[int]:
        if self.max_sample_gap_ms is None:
            return None
        return self.max_sample_gap_ms * 1_000_000


class AS5600LEncoderConfig(DriveEncoderConfigBase):
    driver: Literal["as5600l"] = "as5600l"
    bus: IC2Bus = 1
    address: AddressField = "0x40"
    max_sample_gap_ms: Annotated[Optional[int], Field(gt=0, le=10_000)] = 100
    max_abs_speed_rps: Annotated[Optional[float], Field(gt=0, allow_inf_nan=False)] = (
        5.0
    )

    @field_validator("address", mode="before")
    @classmethod
    def validate_address(cls, value: AddressField) -> AddressField:
        parsed = int(value, 16) if isinstance(value, str) else value
        if parsed < 0 or parsed > 0x7F:
            raise ValueError("AS5600L address must be in the range 0x00 through 0x7F")
        return value

    @property
    def address_int(self) -> int:
        return self.address if isinstance(self.address, int) else int(self.address, 16)

    @property
    def max_sample_gap_ns(self) -> Optional[int]:
        if self.max_sample_gap_ms is None:
            return None
        return self.max_sample_gap_ms * 1_000_000


class GPIOQuadratureEncoderConfig(DriveEncoderConfigBase):
    driver: Literal["gpio_quadrature"] = "gpio_quadrature"
    a_pin: GPIOPin
    b_pin: GPIOPin
    decode_mode: Literal["x1", "x2", "x4"] = "x4"
    pull_up: bool = False
    active_state: Optional[bool] = None

    @model_validator(mode="after")
    def validate_distinct_pins(self) -> Self:
        if _gpio_pin_key(self.a_pin) == _gpio_pin_key(self.b_pin):
            raise ValueError("quadrature A and B pins must be different")
        return self


class MockEncoderConfig(DriveEncoderConfigBase):
    driver: Literal["mock"] = "mock"
    initial_ticks: int = 0
    ticks_per_sample: int = 0


DriveEncoderDeviceConfig = Annotated[
    Union[
        AS5048AEncoderConfig,
        AS5600LEncoderConfig,
        GPIOQuadratureEncoderConfig,
        MockEncoderConfig,
    ],
    Field(discriminator="driver"),
]


class SteeringCalibrationPointConfig(BaseModel):
    sensor_offset_deg: FiniteFloat
    wheel_angle_rad: FiniteFloat


class SteeringPositionConfigBase(BaseModel):
    enabled: EnabledField = False
    sample_frequency_hz: Annotated[float, Field(ge=1, le=500, allow_inf_nan=False)] = (
        100.0
    )
    center_angle_deg: FiniteFloat = 0.0
    invert_direction: bool = False
    wheel_degrees_per_sensor_degree: Annotated[
        float, Field(gt=0, allow_inf_nan=False)
    ] = 1.0
    calibration_points: Annotated[
        List[SteeringCalibrationPointConfig], Field(max_length=20)
    ] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_calibration_points(self) -> Self:
        if len(self.calibration_points) == 1:
            raise ValueError(
                "steering calibration requires zero or at least two points"
            )
        offsets = [point.sensor_offset_deg for point in self.calibration_points]
        if any(right <= left for left, right in zip(offsets, offsets[1:])):
            raise ValueError("steering calibration sensor offsets must increase")
        return self


class AS5048ASteeringPositionConfig(SteeringPositionConfigBase):
    driver: Literal["as5048a"] = "as5048a"
    bus: Annotated[int, Field(ge=0)] = 0
    device: Annotated[int, Field(ge=0)] = 0
    max_speed_hz: Annotated[int, Field(gt=0, le=10_000_000)] = 1_000_000


class AS5600LSteeringPositionConfig(SteeringPositionConfigBase):
    driver: Literal["as5600l"] = "as5600l"
    bus: IC2Bus = 1
    address: AddressField = "0x40"

    @field_validator("address", mode="before")
    @classmethod
    def validate_address(cls, value: AddressField) -> AddressField:
        parsed = int(value, 16) if isinstance(value, str) else value
        if parsed < 0 or parsed > 0x7F:
            raise ValueError("AS5600L address must be in the range 0x00 through 0x7F")
        return value

    @property
    def address_int(self) -> int:
        return self.address if isinstance(self.address, int) else int(self.address, 16)


class MockSteeringPositionConfig(SteeringPositionConfigBase):
    driver: Literal["mock"] = "mock"
    initial_angle_degrees: FiniteFloat = 0.0
    degrees_per_sample: FiniteFloat = 0.0


SteeringPositionConfig = Annotated[
    Union[
        AS5048ASteeringPositionConfig,
        AS5600LSteeringPositionConfig,
        MockSteeringPositionConfig,
    ],
    Field(discriminator="driver"),
]


class EncoderSensorConfig(BaseModel):
    """One or two independently acquired rear wheel/outdrive encoders."""

    enabled: EnabledField = False
    frame_id: str = "rear_axle"
    sample_frequency_hz: Annotated[float, Field(ge=1, le=1000, allow_inf_nan=False)] = (
        100.0
    )
    sensors: Annotated[
        List[DriveEncoderDeviceConfig],
        Field(
            min_length=0,
            max_length=2,
            json_schema_extra={
                "props": {
                    "addLabel": "Add wheel encoder",
                    "itemLabel": "Wheel encoder",
                }
            },
        ),
    ] = Field(default_factory=list)

    @field_validator("frame_id")
    @classmethod
    def validate_frame_id(cls, value: str) -> str:
        return _validate_frame_id(value)

    @model_validator(mode="after")
    def validate_sensor_pair(self) -> Self:
        if self.enabled and not self.sensors:
            raise ValueError("enabled drive encoder acquisition requires a sensor")
        sides = [sensor.side for sensor in self.sensors]
        if len(sides) != len(set(sides)):
            raise ValueError("drive encoder sides must be unique")
        spi_devices = [
            (sensor.bus, sensor.device)
            for sensor in self.sensors
            if isinstance(sensor, AS5048AEncoderConfig)
        ]
        if len(spi_devices) != len(set(spi_devices)):
            raise ValueError("AS5048A encoders must use unique SPI bus/device pairs")
        i2c_devices = [
            (sensor.bus, sensor.address_int)
            for sensor in self.sensors
            if isinstance(sensor, AS5600LEncoderConfig)
        ]
        if len(i2c_devices) != len(set(i2c_devices)):
            raise ValueError("AS5600L encoders must use unique I2C bus/address pairs")
        gpio_pins = [
            _gpio_pin_key(pin)
            for sensor in self.sensors
            if isinstance(sensor, GPIOQuadratureEncoderConfig)
            for pin in (sensor.a_pin, sensor.b_pin)
        ]
        if len(gpio_pins) != len(set(gpio_pins)):
            raise ValueError("GPIO quadrature encoders must use unique A/B pins")
        return self


class LocalizationSensorsConfig(BaseModel):
    lidar: LidarSensorConfig = Field(default_factory=RPLidarC1SensorConfig)
    imu: IMUSensorConfig = Field(default_factory=SH3001SensorConfig)
    encoder: EncoderSensorConfig = Field(default_factory=EncoderSensorConfig)
    steering: SteeringPositionConfig = Field(
        default_factory=AS5048ASteeringPositionConfig
    )

    @model_validator(mode="after")
    def validate_hardware_resources(self) -> Self:
        devices = (
            [
                (sensor.bus, sensor.device, f"rear {sensor.side}")
                for sensor in self.encoder.sensors
                if isinstance(sensor, AS5048AEncoderConfig)
            ]
            if self.encoder.enabled
            else []
        )
        if isinstance(self.steering, AS5048ASteeringPositionConfig):
            devices.append((self.steering.bus, self.steering.device, "steering"))
        enabled_devices = [
            (bus, device, name)
            for bus, device, name in devices
            if name != "steering" or self.steering.enabled
        ]
        keys = [(bus, device) for bus, device, _name in enabled_devices]
        if len(keys) != len(set(keys)):
            raise ValueError(
                "enabled AS5048A sensors must use unique SPI bus/device pairs"
            )
        i2c_devices = []
        if self.imu.enabled and isinstance(self.imu, SH3001SensorConfig):
            i2c_devices.append((self.imu.bus, self.imu.address_int, "imu"))
        if self.encoder.enabled:
            i2c_devices.extend(
                (sensor.bus, sensor.address_int, f"rear {sensor.side}")
                for sensor in self.encoder.sensors
                if isinstance(sensor, AS5600LEncoderConfig)
            )
        if self.steering.enabled and isinstance(
            self.steering, AS5600LSteeringPositionConfig
        ):
            i2c_devices.append(
                (self.steering.bus, self.steering.address_int, "steering")
            )
        i2c_keys = [(bus, address) for bus, address, _name in i2c_devices]
        if len(i2c_keys) != len(set(i2c_keys)):
            raise ValueError(
                "enabled I2C localization sensors must use unique bus/address pairs"
            )
        return self


__all__ = [
    "AS5048AEncoderConfig",
    "AS5048ASteeringPositionConfig",
    "AS5600LEncoderConfig",
    "AS5600LSteeringPositionConfig",
    "DriveEncoderDeviceConfig",
    "EncoderSensorConfig",
    "GPIOQuadratureEncoderConfig",
    "IMUSensorConfig",
    "LidarSensorConfig",
    "LocalizationSensorsConfig",
    "MockEncoderConfig",
    "MockIMUSensorConfig",
    "MockLidarSensorConfig",
    "MockSteeringPositionConfig",
    "RPLidarC1SensorConfig",
    "SH3001SensorConfig",
    "StaticTransformConfig",
    "SteeringCalibrationPointConfig",
    "SteeringPositionConfig",
]
