"""Opt-in real and simulated localization-sensor settings."""

from typing import List, Literal, Optional, Tuple, Union

from app.schemas.robot.common import AddressField, EnabledField, IC2Bus
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Annotated, Self

FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
Vector3 = Tuple[FiniteFloat, FiniteFloat, FiniteFloat]
GPIOPin = Annotated[
    Union[
        Annotated[int, Field(ge=0)],
        Annotated[str, Field(min_length=1)],
    ],
    Field(
        title="GPIO pin",
        description="GPIO number or platform pin name used by the encoder channel.",
        json_schema_extra={"x-ui-type": "pin"},
    ),
]
FrameId = Annotated[
    str,
    Field(
        title="Frame ID",
        description=(
            "Relative coordinate-frame name assigned to published measurements; "
            "do not include a leading slash."
        ),
        min_length=1,
        json_schema_extra={"shared": True},
    ),
]
LidarMinimumRange = Annotated[
    Optional[float],
    Field(
        title="Minimum range",
        description=(
            "Shortest valid LiDAR return in metres. Leave empty to require an "
            "explicit value before enabling the sensor."
        ),
        ge=0,
        allow_inf_nan=False,
        json_schema_extra={"shared": True},
    ),
]
LidarMaximumRange = Annotated[
    Optional[float],
    Field(
        title="Maximum range",
        description=(
            "Longest valid LiDAR return in metres. Leave empty to require an "
            "explicit value before enabling the sensor."
        ),
        gt=0,
        allow_inf_nan=False,
        json_schema_extra={"shared": True},
    ),
]
LidarAngularResolution = Annotated[
    float,
    Field(
        title="Angular resolution",
        description="Angular spacing in degrees between published scan bins.",
        gt=0,
        le=45,
        allow_inf_nan=False,
        json_schema_extra={"shared": True},
    ),
]
MinimumScanMeasurements = Annotated[
    int,
    Field(
        title="Minimum scan measurements",
        description=(
            "Discard a scan when it contains fewer valid measurements than this "
            "threshold."
        ),
        ge=1,
        le=10_000,
        json_schema_extra={"shared": True},
    ),
]
IMUSampleFrequency = Annotated[
    float,
    Field(
        title="IMU sample frequency",
        description="Requested inertial measurement publication rate in hertz.",
        ge=1,
        le=500,
        allow_inf_nan=False,
        json_schema_extra={"shared": True},
    ),
]
LocalizationI2CBus = Annotated[
    IC2Bus,
    Field(
        title="I2C bus",
        description="Linux I2C bus number connected to the localization sensor.",
        json_schema_extra={"shared": True},
    ),
]
EncoderSide = Annotated[
    Literal["left", "right"],
    Field(
        title="Driven side",
        description="Rear wheel or outdrive measured by this encoder.",
        json_schema_extra={"shared": True},
    ),
]
InvertDirection = Annotated[
    bool,
    Field(
        title="Invert direction",
        description="Reverse the sign of measurements reported by this sensor.",
        json_schema_extra={"shared": True},
    ),
]
SPIBus = Annotated[
    int,
    Field(
        title="SPI bus",
        description="Linux SPI bus number connected to the sensor.",
        ge=0,
        json_schema_extra={"shared": True},
    ),
]
SPIDevice = Annotated[
    int,
    Field(
        title="SPI device",
        description="SPI chip-select device number used by the sensor.",
        ge=0,
        json_schema_extra={"shared": True},
    ),
]
SPIMaxSpeed = Annotated[
    int,
    Field(
        title="Maximum SPI clock",
        description="Maximum SPI clock frequency in hertz.",
        gt=0,
        le=10_000_000,
        json_schema_extra={"shared": True},
    ),
]
MaximumSampleGap = Annotated[
    Optional[int],
    Field(
        title="Maximum sample gap",
        description=(
            "Re-baseline without adding motion when consecutive samples are this "
            "many milliseconds apart; leave empty to disable this scheduling limit."
        ),
        gt=0,
        le=10_000,
        json_schema_extra={"shared": True},
    ),
]
MaximumAbsoluteSpeed = Annotated[
    Optional[float],
    Field(
        title="Maximum absolute speed",
        description=(
            "Expected physical speed limit in revolutions per second, used to derive "
            "the maximum unambiguous interval between absolute-angle samples. Leave "
            "empty to disable this derived limit."
        ),
        gt=0,
        allow_inf_nan=False,
        json_schema_extra={"shared": True},
    ),
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
    """Measured pose of a sensor frame in base_link coordinates.

    Sensor-native vectors are rotated into base_link using the configured
    roll, pitch, and yaw in Rz * Ry * Rx order.
    """

    x_m: Annotated[
        FiniteFloat,
        Field(
            title="X position",
            description="Sensor-frame X position in metres relative to base_link.",
        ),
    ] = 0.0
    y_m: Annotated[
        FiniteFloat,
        Field(
            title="Y position",
            description="Sensor-frame Y position in metres relative to base_link.",
        ),
    ] = 0.0
    z_m: Annotated[
        FiniteFloat,
        Field(
            title="Z position",
            description="Sensor-frame Z position in metres relative to base_link.",
        ),
    ] = 0.0
    roll_rad: Annotated[
        FiniteFloat,
        Field(
            title="Roll",
            description="Sensor-frame roll rotation in radians about its X axis.",
        ),
    ] = 0.0
    pitch_rad: Annotated[
        FiniteFloat,
        Field(
            title="Pitch",
            description="Sensor-frame pitch rotation in radians about its Y axis.",
        ),
    ] = 0.0
    yaw_rad: Annotated[
        FiniteFloat,
        Field(
            title="Yaw",
            description="Sensor-frame yaw rotation in radians about its Z axis.",
        ),
    ] = 0.0


SensorTransform = Annotated[
    StaticTransformConfig,
    Field(
        title="Sensor transform",
        description="Measured position and orientation of the sensor in base_link.",
        json_schema_extra={"shared": True},
    ),
]


class LidarSensorConfigBase(BaseModel):
    enabled: EnabledField = False
    frame_id: FrameId = "laser"
    transform: SensorTransform = Field(default_factory=StaticTransformConfig)
    range_min_m: LidarMinimumRange = None
    range_max_m: LidarMaximumRange = None
    angular_resolution_deg: LidarAngularResolution = 1.0
    min_measurements_per_scan: MinimumScanMeasurements = 50

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
    """Serial RPLIDAR C1 scan acquisition for mapping and motion safety."""

    model_config = ConfigDict(title="RPLIDAR C1")

    driver: Annotated[
        Literal["rplidar_c1"],
        Field(
            title="LiDAR driver",
            description="Hardware driver used to acquire LiDAR scans.",
        ),
    ] = "rplidar_c1"
    port: Annotated[
        str,
        Field(
            title="Serial port",
            description="Prefer a stable /dev/serial/by-id path when available.",
            min_length=1,
        ),
    ] = "/dev/ttyUSB0"
    baudrate: Annotated[
        int,
        Field(
            title="Serial baud rate",
            description="Serial communication speed in bits per second.",
            gt=0,
        ),
    ] = 460800
    timeout_s: Annotated[
        float,
        Field(
            title="Serial timeout",
            description="Maximum time in seconds to wait for serial scan data.",
            gt=0,
            le=10,
            allow_inf_nan=False,
        ),
    ] = 1.0


class MockLidarSensorConfig(LidarSensorConfigBase):
    """Uniform circular scan for mapping, safety, and telemetry development."""

    model_config = ConfigDict(title="Mock LiDAR")

    driver: Annotated[
        Literal["mock"],
        Field(
            title="LiDAR driver",
            description="Simulated driver used to generate LiDAR scans.",
        ),
    ] = "mock"
    range_min_m: LidarMinimumRange = 0.05
    range_max_m: LidarMaximumRange = 12.0
    points_per_scan: Annotated[
        int,
        Field(
            title="Points per scan",
            description="Number of evenly spaced returns in each simulated scan.",
            ge=8,
            le=1440,
        ),
    ] = 360
    distance_m: Annotated[
        float,
        Field(
            title="Simulated distance",
            description="Uniform range in metres reported by every simulated ray.",
            ge=0,
            allow_inf_nan=False,
        ),
    ] = 2.0
    quality: Annotated[
        int,
        Field(
            title="Return quality",
            description="Quality value assigned to every simulated LiDAR return.",
            ge=0,
            le=255,
        ),
    ] = 100
    scan_frequency_hz: Annotated[
        float,
        Field(
            title="Scan frequency",
            description="Rate in hertz at which simulated scans are published.",
            gt=0,
            le=30,
            allow_inf_nan=False,
        ),
    ] = 10.0
    min_measurements_per_scan: MinimumScanMeasurements = 50


LidarSensorConfig = Annotated[
    Union[RPLidarC1SensorConfig, MockLidarSensorConfig],
    Field(discriminator="driver"),
]


class IMUSensorConfigBase(BaseModel):
    enabled: EnabledField = False
    frame_id: FrameId = "imu"
    transform: SensorTransform = Field(default_factory=StaticTransformConfig)
    sample_frequency_hz: IMUSampleFrequency = 100.0

    @field_validator("frame_id")
    @classmethod
    def validate_frame_id(cls, value: str) -> str:
        return _validate_frame_id(value)


class SH3001SensorConfig(IMUSensorConfigBase):
    """Six-axis inertial measurements from a SunFounder Robot HAT SH3001."""

    model_config = ConfigDict(title="SH3001 IMU")

    driver: Annotated[
        Literal["sh3001"],
        Field(
            title="IMU driver",
            description="Hardware driver used to acquire inertial measurements.",
        ),
    ] = "sh3001"
    bus: LocalizationI2CBus = 1
    address: Annotated[
        AddressField,
        Field(
            title="I2C address",
            description="7-bit I2C address of the SH3001 IMU.",
        ),
    ] = "0x36"
    accelerometer_range_g: Annotated[
        Literal[2, 4, 8, 16],
        Field(
            title="Accelerometer range",
            description=(
                "Full-scale acceleration range in multiples of standard gravity. "
                "Lower ranges provide finer resolution."
            ),
        ),
    ] = 2
    gyroscope_range_dps: Annotated[
        Literal[125, 250, 500, 1000, 2000],
        Field(
            title="Gyroscope range",
            description=(
                "Full-scale angular-rate range in degrees per second. Lower ranges "
                "provide finer resolution."
            ),
        ),
    ] = 2000

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


class LSM9DS1SensorConfig(IMUSensorConfigBase):
    """Six-axis IMU settings for a Sense HAT or standalone LSM9DS1."""

    model_config = ConfigDict(title="LSM9DS1 IMU")

    driver: Annotated[
        Literal["lsm9ds1"],
        Field(
            title="IMU driver",
            description="Hardware driver used to acquire inertial measurements.",
        ),
    ] = "lsm9ds1"
    bus: LocalizationI2CBus = 1
    address: Annotated[
        AddressField,
        Field(
            title="I2C address",
            description="7-bit I2C address of the LSM9DS1 inertial die (0x6A or 0x6B).",
        ),
    ] = "0x6a"
    accelerometer_range_g: Annotated[
        Literal[2, 4, 8, 16],
        Field(
            title="Accelerometer range",
            description=(
                "Full-scale acceleration range in multiples of standard gravity. "
                "Lower ranges provide finer resolution."
            ),
        ),
    ] = 2
    gyroscope_range_dps: Annotated[
        Literal[245, 500, 2000],
        Field(
            title="Gyroscope range",
            description=(
                "Full-scale angular-rate range in degrees per second. Lower ranges "
                "provide finer resolution."
            ),
        ),
    ] = 245
    output_data_rate_hz: Annotated[
        Literal[119, 238, 476, 952],
        Field(
            title="Output data rate",
            description=(
                "Hardware accelerometer and gyroscope output rate in hertz. It "
                "must be at least the requested IMU sample frequency."
            ),
        ),
    ] = 119

    @field_validator("address", mode="before")
    @classmethod
    def validate_address(cls, value: AddressField) -> AddressField:
        if isinstance(value, str):
            try:
                parsed = int(value, 16)
            except ValueError as error:
                raise ValueError(
                    "LSM9DS1 address must be an integer or hexadecimal"
                ) from error
        else:
            parsed = value
        if parsed not in (0x6A, 0x6B):
            raise ValueError("LSM9DS1 address must be 0x6A or 0x6B")
        return value

    @model_validator(mode="after")
    def require_output_rate_for_requested_sample_rate(self) -> Self:
        if self.sample_frequency_hz > self.output_data_rate_hz:
            raise ValueError(
                "LSM9DS1 output_data_rate_hz must be at least sample_frequency_hz"
            )
        return self

    @property
    def address_int(self) -> int:
        return self.address if isinstance(self.address, int) else int(self.address, 16)


class MockIMUSensorConfig(IMUSensorConfigBase):
    """Fixed inertial measurements for development without IMU hardware."""

    model_config = ConfigDict(title="Mock IMU")

    driver: Annotated[
        Literal["mock"],
        Field(
            title="IMU driver",
            description="Simulated driver used to generate inertial measurements.",
        ),
    ] = "mock"
    acceleration_mps2: Annotated[
        Vector3,
        Field(
            title="Acceleration vector",
            description=(
                "Fixed simulated X, Y, and Z acceleration components in metres per "
                "second squared."
            ),
            examples=[[0.0, 0.0, 9.80665]],
        ),
    ] = (0.0, 0.0, 9.80665)
    angular_velocity_radps: Annotated[
        Vector3,
        Field(
            title="Angular velocity vector",
            description=(
                "Fixed simulated X, Y, and Z angular velocity components in radians "
                "per second."
            ),
            examples=[[0.0, 0.0, 0.0]],
        ),
    ] = (0.0, 0.0, 0.0)


IMUSensorConfig = Annotated[
    Union[SH3001SensorConfig, LSM9DS1SensorConfig, MockIMUSensorConfig],
    Field(discriminator="driver"),
]


class DriveEncoderConfigBase(BaseModel):
    side: EncoderSide
    invert_direction: InvertDirection = False


class AS5048AEncoderConfig(DriveEncoderConfigBase):
    """Rear drive position and speed from an AS5048A SPI magnetic encoder."""

    model_config = ConfigDict(title="AS5048A drive encoder")

    driver: Annotated[
        Literal["as5048a"],
        Field(
            title="Encoder driver",
            description="Hardware driver used to acquire drive-encoder samples.",
        ),
    ] = "as5048a"
    bus: SPIBus = 0
    device: SPIDevice = 0
    max_speed_hz: SPIMaxSpeed = 1_000_000
    max_sample_gap_ms: MaximumSampleGap = 100
    max_abs_speed_rps: MaximumAbsoluteSpeed = 5.0

    @property
    def max_sample_gap_ns(self) -> Optional[int]:
        if self.max_sample_gap_ms is None:
            return None
        return self.max_sample_gap_ms * 1_000_000


class AS5600LEncoderConfig(DriveEncoderConfigBase):
    """Rear drive position and speed from an AS5600L I2C magnetic encoder."""

    model_config = ConfigDict(title="AS5600L drive encoder")

    driver: Annotated[
        Literal["as5600l"],
        Field(
            title="Encoder driver",
            description="Hardware driver used to acquire drive-encoder samples.",
        ),
    ] = "as5600l"
    bus: LocalizationI2CBus = 1
    address: Annotated[
        AddressField,
        Field(
            title="I2C address",
            description="Programmable 7-bit I2C address of the AS5600L encoder.",
        ),
    ] = "0x40"
    max_sample_gap_ms: MaximumSampleGap = 100
    max_abs_speed_rps: MaximumAbsoluteSpeed = 5.0

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
    """Incremental rear drive position from two GPIO quadrature channels."""

    model_config = ConfigDict(title="GPIO quadrature drive encoder")

    driver: Annotated[
        Literal["gpio_quadrature"],
        Field(
            title="Encoder driver",
            description="Hardware driver used to acquire drive-encoder samples.",
        ),
    ] = "gpio_quadrature"
    a_pin: Annotated[
        GPIOPin,
        Field(
            title="Channel A GPIO pin",
            description="GPIO number or platform pin name for quadrature channel A.",
        ),
    ]
    b_pin: Annotated[
        GPIOPin,
        Field(
            title="Channel B GPIO pin",
            description="GPIO number or platform pin name for quadrature channel B.",
        ),
    ]
    decode_mode: Annotated[
        Literal["x1", "x2", "x4"],
        Field(
            title="Quadrature decode mode",
            description=(
                "Number of signal edges counted per encoder cycle: x1 counts one, "
                "x2 counts two, and x4 counts all four."
            ),
        ),
    ] = "x4"
    pull_up: Annotated[
        bool,
        Field(
            title="Enable pull-ups",
            description="Enable internal pull-up resistors on both GPIO inputs.",
        ),
    ] = False
    active_state: Annotated[
        Optional[bool],
        Field(
            title="Active state",
            description=(
                "Optional active logic level passed to the GPIO backend; leave empty "
                "to use edge transitions without an active-state override."
            ),
        ),
    ] = None

    @model_validator(mode="after")
    def validate_distinct_pins(self) -> Self:
        if _gpio_pin_key(self.a_pin) == _gpio_pin_key(self.b_pin):
            raise ValueError("quadrature A and B pins must be different")
        return self


class MockEncoderConfig(DriveEncoderConfigBase):
    """Deterministic encoder ticks for development without encoder hardware."""

    model_config = ConfigDict(title="Mock drive encoder")

    driver: Annotated[
        Literal["mock"],
        Field(
            title="Encoder driver",
            description="Simulated driver used to generate drive-encoder samples.",
        ),
    ] = "mock"
    initial_ticks: Annotated[
        int,
        Field(
            title="Initial ticks",
            description="Encoder tick count reported by the first simulated sample.",
        ),
    ] = 0
    ticks_per_sample: Annotated[
        int,
        Field(
            title="Ticks per sample",
            description="Signed tick increment applied to each simulated sample.",
        ),
    ] = 0


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
    """One measured relationship between sensor offset and front-wheel angle."""

    model_config = ConfigDict(title="Steering calibration point")

    sensor_offset_deg: Annotated[
        FiniteFloat,
        Field(
            title="Sensor offset",
            description="Signed sensor displacement in degrees from its center value.",
        ),
    ]
    wheel_angle_rad: Annotated[
        FiniteFloat,
        Field(
            title="Wheel angle",
            description=(
                "Measured signed front-wheel steering angle in radians at this "
                "sensor offset."
            ),
        ),
    ]


class SteeringPositionConfigBase(BaseModel):
    enabled: EnabledField = False
    sample_frequency_hz: Annotated[
        float,
        Field(
            title="Steering sample frequency",
            description="Requested steering-position publication rate in hertz.",
            ge=1,
            le=500,
            allow_inf_nan=False,
            json_schema_extra={"shared": True},
        ),
    ] = 100.0
    center_angle_deg: Annotated[
        FiniteFloat,
        Field(
            title="Sensor center angle",
            description=(
                "Raw sensor angle in degrees corresponding to straight-ahead steering."
            ),
            json_schema_extra={"shared": True},
        ),
    ] = 0.0
    invert_direction: InvertDirection = False
    wheel_degrees_per_sensor_degree: Annotated[
        float,
        Field(
            title="Wheel-to-sensor angle ratio",
            description=(
                "Front-wheel angle change in degrees per degree of sensor movement "
                "when no calibration table is configured."
            ),
            gt=0,
            allow_inf_nan=False,
            json_schema_extra={"shared": True},
        ),
    ] = 1.0
    calibration_points: Annotated[
        List[SteeringCalibrationPointConfig],
        Field(
            title="Steering calibration points",
            description=(
                "Optional piecewise-linear mapping from sensor offset to measured "
                "front-wheel angle. Use zero points for the fixed ratio or provide "
                "at least two points in increasing sensor-offset order."
            ),
            max_length=20,
            json_schema_extra={
                "shared": True,
                "props": {
                    "addLabel": "Add calibration point",
                    "itemLabel": "Calibration point",
                },
            },
        ),
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
    """Front steering position from an AS5048A SPI magnetic encoder."""

    model_config = ConfigDict(title="AS5048A steering position")

    driver: Annotated[
        Literal["as5048a"],
        Field(
            title="Steering sensor driver",
            description="Hardware driver used to acquire steering position.",
        ),
    ] = "as5048a"
    bus: SPIBus = 0
    device: SPIDevice = 0
    max_speed_hz: SPIMaxSpeed = 1_000_000


class AS5600LSteeringPositionConfig(SteeringPositionConfigBase):
    """Front steering position from an AS5600L I2C magnetic encoder."""

    model_config = ConfigDict(title="AS5600L steering position")

    driver: Annotated[
        Literal["as5600l"],
        Field(
            title="Steering sensor driver",
            description="Hardware driver used to acquire steering position.",
        ),
    ] = "as5600l"
    bus: LocalizationI2CBus = 1
    address: Annotated[
        AddressField,
        Field(
            title="I2C address",
            description="Programmable 7-bit I2C address of the AS5600L encoder.",
        ),
    ] = "0x40"

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
    """Deterministic steering angles for development without position hardware."""

    model_config = ConfigDict(title="Mock steering position")

    driver: Annotated[
        Literal["mock"],
        Field(
            title="Steering sensor driver",
            description="Simulated driver used to generate steering position.",
        ),
    ] = "mock"
    initial_angle_degrees: Annotated[
        FiniteFloat,
        Field(
            title="Initial sensor angle",
            description="Raw sensor angle in degrees reported by the first sample.",
        ),
    ] = 0.0
    degrees_per_sample: Annotated[
        FiniteFloat,
        Field(
            title="Degrees per sample",
            description="Signed sensor-angle increment applied to each sample.",
        ),
    ] = 0.0


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
    frame_id: FrameId = "rear_axle"
    sample_frequency_hz: Annotated[
        float,
        Field(
            title="Encoder sample frequency",
            description="Requested drive-encoder publication rate in hertz.",
            ge=1,
            le=1000,
            allow_inf_nan=False,
        ),
    ] = 100.0
    sensors: Annotated[
        List[DriveEncoderDeviceConfig],
        Field(
            title="Drive encoders",
            description=(
                "One or two rear wheel or outdrive encoders. Configured sides and "
                "hardware resources must be unique."
            ),
            min_length=0,
            max_length=2,
            json_schema_extra={
                "props": {
                    "addLabel": "Add wheel encoder",
                    "itemLabel": "Wheel encoder",
                    "typeLabel": "Encoder type",
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
    """LiDAR, inertial, drive-encoder, and steering-position acquisition."""

    lidar: Annotated[
        LidarSensorConfig,
        Field(
            title="LiDAR sensor",
            description="Scan source used by mapping, telemetry, and motion safety.",
        ),
    ] = Field(default_factory=RPLidarC1SensorConfig)
    imu: Annotated[
        IMUSensorConfig,
        Field(
            title="Inertial measurement unit",
            description="Acceleration and angular-velocity source for pose estimation.",
        ),
    ] = Field(default_factory=SH3001SensorConfig)
    encoder: Annotated[
        EncoderSensorConfig,
        Field(
            title="Drive encoders",
            description="Rear wheel or outdrive position and speed acquisition.",
        ),
    ] = Field(default_factory=EncoderSensorConfig)
    steering: Annotated[
        SteeringPositionConfig,
        Field(
            title="Steering position sensor",
            description="Measured front-wheel steering position acquisition.",
        ),
    ] = Field(
        default_factory=AS5048ASteeringPositionConfig,
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
        if self.imu.enabled and isinstance(
            self.imu, (SH3001SensorConfig, LSM9DS1SensorConfig)
        ):
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
    "LSM9DS1SensorConfig",
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
