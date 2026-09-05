"""Configuration for non-localization environmental and magnetic sensors."""

from enum import Enum
from typing import List, Literal, Optional, Tuple, Union

from app.schemas.robot.common import AddressField, EnabledField, IC2Bus
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Annotated, Self

FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
Vector3 = Tuple[FiniteFloat, FiniteFloat, FiniteFloat]

SensorName = Annotated[
    str,
    Field(
        title="Sensor name",
        description=(
            "Unique display name used to identify this sensor in telemetry and "
            "the controller UI."
        ),
        min_length=1,
        max_length=80,
        json_schema_extra={"shared": True},
    ),
]
PollIntervalSeconds = Annotated[
    float,
    Field(
        title="Telemetry interval",
        description=(
            "Minimum time in seconds between fresh sensor readings sent to the browser."
        ),
        ge=0.05,
        le=3600,
        allow_inf_nan=False,
        examples=[1.0],
        json_schema_extra={"shared": True},
    ),
]
I2CBusField = Annotated[
    IC2Bus,
    Field(
        title="I2C bus",
        description="Linux I2C bus number used to communicate with the sensor.",
        json_schema_extra={"shared": True},
    ),
]


class HTS221OutputDataRate(float, Enum):
    HZ_1 = 1.0
    HZ_7 = 7.0
    HZ_12_5 = 12.5


class LPS25HOutputDataRate(float, Enum):
    HZ_1 = 1.0
    HZ_7 = 7.0
    HZ_12_5 = 12.5
    HZ_25 = 25.0


class LSM9DS1MagnetometerOutputDataRate(float, Enum):
    HZ_0_625 = 0.625
    HZ_1_25 = 1.25
    HZ_2_5 = 2.5
    HZ_5 = 5.0
    HZ_10 = 10.0
    HZ_20 = 20.0
    HZ_40 = 40.0
    HZ_80 = 80.0


def _parse_address(value: AddressField, *, device: str) -> int:
    if isinstance(value, str):
        try:
            return int(value, 16)
        except ValueError as error:
            raise ValueError(
                f"{device} address must be an integer or hexadecimal"
            ) from error
    return value


class AuxiliarySensorConfigBase(BaseModel):
    name: SensorName
    enabled: EnabledField = True
    poll_interval_seconds: PollIntervalSeconds = 1.0

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("sensor name must not be blank")
        return name


class I2CAuxiliarySensorConfig(AuxiliarySensorConfigBase):
    bus: I2CBusField = 1
    address: AddressField

    @property
    def address_int(self) -> int:
        return self.address if isinstance(self.address, int) else int(self.address, 16)


class HTS221SensorConfig(I2CAuxiliarySensorConfig):
    """Temperature and relative-humidity readings from an HTS221 sensor."""

    model_config = ConfigDict(title="Temperature/humidity (HTS221)")

    driver: Annotated[
        Literal["hts221"],
        Field(
            title="Sensor driver",
            description="Hardware driver used for this sensor.",
        ),
    ] = "hts221"
    name: SensorName = "HTS221"
    address: Annotated[
        AddressField,
        Field(
            title="I2C address",
            description="Fixed 7-bit I2C address of the HTS221 sensor (0x5F).",
        ),
    ] = "0x5f"
    output_data_rate_hz: Annotated[
        HTS221OutputDataRate,
        Field(
            title="Output data rate",
            description=(
                "Number of new temperature and humidity measurements produced "
                "per second. It must be at least the requested telemetry rate."
            ),
        ),
    ] = HTS221OutputDataRate.HZ_1
    humidity_average_samples: Annotated[
        Literal[4, 8, 16, 32, 64, 128, 256, 512],
        Field(
            title="Humidity averaging samples",
            description=(
                "Number of internal samples averaged for each humidity reading. "
                "Higher values reduce noise but respond more slowly."
            ),
        ),
    ] = 32
    temperature_average_samples: Annotated[
        Literal[2, 4, 8, 16, 32, 64, 128, 256],
        Field(
            title="Temperature averaging samples",
            description=(
                "Number of internal samples averaged for each temperature "
                "reading. Higher values reduce noise but respond more slowly."
            ),
        ),
    ] = 16

    @field_validator("address", mode="before")
    @classmethod
    def validate_address(cls, value: AddressField) -> AddressField:
        if _parse_address(value, device="HTS221") != 0x5F:
            raise ValueError("HTS221 address must be 0x5F")
        return value

    @model_validator(mode="after")
    def validate_poll_rate(self) -> Self:
        if 1.0 / self.poll_interval_seconds > self.output_data_rate_hz.value:
            raise ValueError("HTS221 poll rate must not exceed output_data_rate_hz")
        return self


class LPS25HSensorConfig(I2CAuxiliarySensorConfig):
    """Pressure and temperature readings from an LPS25H or LPS25HB sensor."""

    model_config = ConfigDict(title="Pressure and temperature (LPS25H/HB)")

    driver: Annotated[
        Literal["lps25h"],
        Field(
            title="Sensor driver",
            description="Hardware driver used for this sensor.",
        ),
    ] = "lps25h"
    name: SensorName = "LPS25H"
    address: Annotated[
        AddressField,
        Field(
            title="I2C address",
            description=(
                "7-bit I2C address of the LPS25H/LPS25HB sensor (0x5C or 0x5D)."
            ),
        ),
    ] = "0x5c"
    output_data_rate_hz: Annotated[
        LPS25HOutputDataRate,
        Field(
            title="Output data rate",
            description=(
                "Number of new pressure and temperature measurements produced per "
                "second. It must be at least the requested telemetry rate."
            ),
        ),
    ] = LPS25HOutputDataRate.HZ_1

    @field_validator("address", mode="before")
    @classmethod
    def validate_address(cls, value: AddressField) -> AddressField:
        if _parse_address(value, device="LPS25H") not in (0x5C, 0x5D):
            raise ValueError("LPS25H/LPS25HB address must be 0x5C or 0x5D")
        return value

    @model_validator(mode="after")
    def validate_poll_rate(self) -> Self:
        if 1.0 / self.poll_interval_seconds > self.output_data_rate_hz.value:
            raise ValueError("LPS25H poll rate must not exceed output_data_rate_hz")
        return self


class LSM9DS1MagnetometerSensorConfig(I2CAuxiliarySensorConfig):
    """Three-axis magnetic-field readings from the LSM9DS1 magnetic die."""

    model_config = ConfigDict(title="Magnetometer (LSM9DS1)")

    driver: Annotated[
        Literal["lsm9ds1_magnetometer"],
        Field(
            title="Sensor driver",
            description="Hardware driver used for this sensor.",
        ),
    ] = "lsm9ds1_magnetometer"
    name: SensorName = "Magnetometer"
    address: Annotated[
        AddressField,
        Field(
            title="I2C address",
            description=(
                "7-bit I2C address of the LSM9DS1 magnetic die (0x1C or 0x1E)."
            ),
        ),
    ] = "0x1c"
    magnetic_field_range_gauss: Annotated[
        Literal[4, 8, 12, 16],
        Field(
            title="Magnetic field range",
            description=(
                "Full-scale magnetic field range in gauss. Lower ranges provide "
                "finer resolution; increase the range if readings saturate."
            ),
        ),
    ] = 4
    output_data_rate_hz: Annotated[
        LSM9DS1MagnetometerOutputDataRate,
        Field(
            title="Output data rate",
            description=(
                "Number of new three-axis magnetic field measurements produced per "
                "second. It must be at least the requested telemetry rate."
            ),
        ),
    ] = LSM9DS1MagnetometerOutputDataRate.HZ_20
    performance_mode: Annotated[
        Literal["low", "medium", "high", "ultra_high"],
        Field(
            title="Performance mode",
            description=(
                "Magnetometer conversion mode for all three axes. Higher modes "
                "reduce measurement noise at the cost of power consumption."
            ),
        ),
    ] = "ultra_high"

    @field_validator("address", mode="before")
    @classmethod
    def validate_address(cls, value: AddressField) -> AddressField:
        if _parse_address(value, device="LSM9DS1 magnetometer") not in (0x1C, 0x1E):
            raise ValueError("LSM9DS1 magnetometer address must be 0x1C or 0x1E")
        return value

    @model_validator(mode="after")
    def validate_poll_rate(self) -> Self:
        if 1.0 / self.poll_interval_seconds > self.output_data_rate_hz.value:
            raise ValueError(
                "LSM9DS1 magnetometer poll rate must not exceed output_data_rate_hz"
            )
        return self


class MockEnvironmentalSensorConfig(AuxiliarySensorConfigBase):
    """Fixed environmental readings for development without sensor hardware."""

    model_config = ConfigDict(title="Mock environmental sensor")

    driver: Annotated[
        Literal["mock_environmental"],
        Field(
            title="Sensor driver",
            description="Simulated driver used for this sensor.",
        ),
    ] = "mock_environmental"
    name: SensorName = "Mock environment"
    temperature_c: Annotated[
        Optional[FiniteFloat],
        Field(
            title="Temperature",
            description=(
                "Fixed simulated temperature in degrees Celsius. Leave empty to "
                "omit temperature from telemetry."
            ),
            examples=[21.0],
        ),
    ] = 21.0
    relative_humidity_percent: Annotated[
        Optional[float],
        Field(
            title="Relative humidity",
            description=(
                "Fixed simulated relative humidity as a percentage. Leave empty "
                "to omit humidity from telemetry."
            ),
            ge=0,
            le=100,
            allow_inf_nan=False,
            examples=[45.0],
        ),
    ] = 45.0
    pressure_pa: Annotated[
        Optional[float],
        Field(
            title="Pressure",
            description=(
                "Fixed simulated absolute pressure in pascals. Leave empty to omit "
                "pressure from telemetry."
            ),
            ge=0,
            allow_inf_nan=False,
            examples=[101_325.0],
        ),
    ] = 101_325.0

    @model_validator(mode="after")
    def require_measurement(self) -> Self:
        if (
            self.temperature_c is None
            and self.relative_humidity_percent is None
            and self.pressure_pa is None
        ):
            raise ValueError("mock environmental sensor requires a measurement")
        return self


class MockMagnetometerSensorConfig(AuxiliarySensorConfigBase):
    """Fixed three-axis magnetic-field readings for hardware-free development."""

    model_config = ConfigDict(title="Mock magnetometer")

    driver: Annotated[
        Literal["mock_magnetometer"],
        Field(
            title="Sensor driver",
            description="Simulated driver used for this sensor.",
        ),
    ] = "mock_magnetometer"
    name: SensorName = "Mock magnetometer"
    magnetic_field_t: Annotated[
        Vector3,
        Field(
            title="Magnetic field vector",
            description=(
                "Fixed simulated X, Y, and Z magnetic field components in teslas."
            ),
            examples=[[20e-6, 0.0, 45e-6]],
        ),
    ] = (20e-6, 0.0, 45e-6)


AuxiliarySensorConfig = Annotated[
    Union[
        HTS221SensorConfig,
        LPS25HSensorConfig,
        LSM9DS1MagnetometerSensorConfig,
        MockEnvironmentalSensorConfig,
        MockMagnetometerSensorConfig,
    ],
    Field(discriminator="driver"),
]


class AuxiliarySensorsConfig(BaseModel):
    """Named environmental and magnetic sensors published as browser telemetry."""

    sensors: Annotated[
        List[AuxiliarySensorConfig],
        Field(
            title="Auxiliary sensors",
            description=(
                "Environmental and magnetic sensors published independently of "
                "localization and odometry."
            ),
            max_length=32,
            json_schema_extra={
                "uniqueItemProperty": "name",
                "props": {
                    "addLabel": "Add sensor",
                    "itemLabel": "Sensor",
                    "typeLabel": "Sensor type",
                },
            },
        ),
    ] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_resources(self) -> Self:
        names = [sensor.name.casefold() for sensor in self.sensors]
        if len(names) != len(set(names)):
            raise ValueError("auxiliary sensor names must be unique")
        devices = [
            (sensor.bus, sensor.address_int)
            for sensor in self.sensors
            if sensor.enabled and isinstance(sensor, I2CAuxiliarySensorConfig)
        ]
        if len(devices) != len(set(devices)):
            raise ValueError(
                "enabled auxiliary I2C sensors must use unique bus/address pairs"
            )
        return self


__all__ = [
    "AuxiliarySensorConfig",
    "AuxiliarySensorsConfig",
    "HTS221SensorConfig",
    "LPS25HSensorConfig",
    "LSM9DS1MagnetometerSensorConfig",
    "MockEnvironmentalSensorConfig",
    "MockMagnetometerSensorConfig",
]
