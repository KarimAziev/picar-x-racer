"""Configuration for non-localization environmental and magnetic sensors."""

from enum import Enum
from typing import List, Literal, Optional, Tuple, Union

from app.schemas.robot.common import AddressField, EnabledField, IC2Bus
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Annotated, Self


FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]
Vector3 = Tuple[FiniteFloat, FiniteFloat, FiniteFloat]


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
    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=80,
            description="Unique human-readable name used in telemetry.",
        ),
    ]
    enabled: EnabledField = True
    poll_interval_seconds: Annotated[
        float,
        Field(
            ge=0.05,
            le=3600,
            allow_inf_nan=False,
            description="Minimum interval between browser telemetry samples.",
        ),
    ] = 1.0

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("sensor name must not be blank")
        return name


class I2CAuxiliarySensorConfig(AuxiliarySensorConfigBase):
    bus: IC2Bus = 1
    address: AddressField

    @property
    def address_int(self) -> int:
        return self.address if isinstance(self.address, int) else int(self.address, 16)


class HTS221SensorConfig(I2CAuxiliarySensorConfig):
    model_config = ConfigDict(title="Sense HAT temperature and humidity (HTS221)")

    driver: Literal["hts221"] = "hts221"
    name: str = "Sense HAT temperature and humidity"
    address: AddressField = "0x5f"
    output_data_rate_hz: HTS221OutputDataRate = HTS221OutputDataRate.HZ_1
    humidity_average_samples: Literal[4, 8, 16, 32, 64, 128, 256, 512] = 32
    temperature_average_samples: Literal[2, 4, 8, 16, 32, 64, 128, 256] = 16

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
    model_config = ConfigDict(title="Sense HAT pressure and temperature (LPS25H/HB)")

    driver: Literal["lps25h"] = "lps25h"
    name: str = "Sense HAT pressure and temperature"
    address: AddressField = "0x5c"
    output_data_rate_hz: LPS25HOutputDataRate = LPS25HOutputDataRate.HZ_1

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
    model_config = ConfigDict(title="Sense HAT magnetic field (LSM9DS1)")

    driver: Literal["lsm9ds1_magnetometer"] = "lsm9ds1_magnetometer"
    name: str = "Sense HAT magnetometer"
    address: AddressField = "0x1c"
    magnetic_field_range_gauss: Literal[4, 8, 12, 16] = 4
    output_data_rate_hz: LSM9DS1MagnetometerOutputDataRate = (
        LSM9DS1MagnetometerOutputDataRate.HZ_20
    )
    performance_mode: Literal["low", "medium", "high", "ultra_high"] = "ultra_high"

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
    model_config = ConfigDict(title="Mock environmental sensor")

    driver: Literal["mock_environmental"] = "mock_environmental"
    name: str = "Mock environment"
    temperature_c: Optional[FiniteFloat] = 21.0
    relative_humidity_percent: Annotated[
        Optional[float], Field(ge=0, le=100, allow_inf_nan=False)
    ] = 45.0
    pressure_pa: Annotated[Optional[float], Field(ge=0, allow_inf_nan=False)] = (
        101_325.0
    )

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
    model_config = ConfigDict(title="Mock magnetometer")

    driver: Literal["mock_magnetometer"] = "mock_magnetometer"
    name: str = "Mock magnetometer"
    magnetic_field_t: Vector3 = (20e-6, 0.0, 45e-6)


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
    sensors: Annotated[
        List[AuxiliarySensorConfig],
        Field(
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
