import re
from typing import Literal, Optional, Union

from app.core.logger import Logger
from app.schemas.distance import UltrasonicConfig
from pydantic import BaseModel, Field, computed_field, field_validator, model_validator
from robot_hat import MotorDirection, ServoCalibrationMode
from robot_hat.drivers.adc.INA219 import ADCResolution, BusVoltageRange, Gain, Mode
from robot_hat.drivers.adc.sunfounder_adc import (
    ADC_ALLOWED_CHANNELS,
    ADC_ALLOWED_CHANNELS_DESCRIPTION,
    ADC_ALLOWED_CHANNELS_PIN_NAMES,
)
from typing_extensions import Annotated

logger = Logger(__name__)

EnabledField = Annotated[
    bool,
    Field(
        ...,
        title="Enabled",
        description="Whether the device is enabled.",
    ),
]

MotorDirectionField = Annotated[
    MotorDirection,
    Field(
        1,
        ge=-1,
        le=1,
        description="Initial motor direction calibration (+1/-1)",
        examples=[1, -1],
    ),
]

AddressField = Annotated[
    Union[int, str],
    Field(
        ...,
        title="I2C address",
        description="I2C address of the device",
        examples=[0x40, "0x40", 64],
        json_schema_extra={"type": "hex"},
    ),
]


class AddressModel(BaseModel):
    address: AddressField

    @field_validator("address", mode="before")
    def parse_hex_address(cls, value):
        if isinstance(value, str):
            if not re.fullmatch(r"0[xX][0-9a-fA-F]+", value):
                raise ValueError(
                    "Address string must be a valid hexadecimal (e.g., '0x40')."
                )

            int_val = int(value, 16)
        else:
            int_val = value

        if int_val < 0:
            raise ValueError("Address must be a positive number.")

        return value

    @computed_field
    @property
    def addr_str(self) -> str:
        if isinstance(self.address, int):
            return hex(self.address)
        return self.address

    @computed_field
    @property
    def addr_int(self) -> int:
        if isinstance(self.address, int):
            return self.address
        return int(self.address, 16)


class PWMDriverConfig(AddressModel):
    """
    Configuration for the driver class that enables control of the chip on the I2C bus.
    """

    name: Annotated[
        Literal["PCA9685", "Sunfounder"],
        Field(
            ...,
            description="Model of the PWM driver chip",
            examples=["Sunfounder", "PCA9685"],
        ),
    ] = "PCA9685"

    bus: Annotated[
        int,
        Field(
            ...,
            title="The I2C bus",
            description="I2C bus number",
            examples=[1, 4],
            ge=0,
        ),
    ] = 1
    frame_width: Annotated[
        Optional[int],
        Field(
            ...,
            title="The Frame Width",
            description="The length of time in microseconds (µs) between servo control pulses.",
            examples=[20000],
            ge=1,
        ),
    ] = 20000
    freq: Annotated[
        int,
        Field(
            ...,
            title="The PWM frequency",
            description="The initial PWM frequency in Hz",
            examples=[50],
            ge=0,
        ),
    ] = 50

    address: AddressField = "0x40"


class INA219Config(BaseModel):
    """
    Configuration for INA219 - a digital current sensor.

    Calibration-related values (current_lsb, calibration_value, power_lsb)
    are tied to the shunt resistor and maximum current measurement range.
    """

    bus_voltage_range: Annotated[
        BusVoltageRange,
        Field(
            ...,
            title="Bus Voltage Range",
            description="Voltage range for the sensor.",
            examples=[BusVoltageRange.RANGE_32V, BusVoltageRange.RANGE_16V],
        ),
    ] = BusVoltageRange.RANGE_32V

    gain: Annotated[
        Gain,
        Field(
            ...,
            title="Gain Setting",
            description=(
                "Gain setting for the shunt voltage measurement. "
                "Options: DIV_1_40MV, DIV_2_80MV, DIV_4_160MV, or DIV_8_320MV (default)."
            ),
            examples=[Gain.DIV_8_320MV],
        ),
    ] = Gain.DIV_8_320MV

    bus_adc_resolution: Annotated[
        ADCResolution,
        Field(
            ...,
            title="Bus ADC Resolution",
            description="ADC resolution/averaging setting for bus voltage measurement.",
            examples=[ADCResolution.ADCRES_12BIT_32S],
        ),
    ] = ADCResolution.ADCRES_12BIT_32S

    shunt_adc_resolution: Annotated[
        ADCResolution,
        Field(
            ...,
            title="Shunt ADC Resolution",
            description="ADC resolution/averaging setting for shunt voltage measurement.",
            examples=[ADCResolution.ADCRES_12BIT_32S],
        ),
    ] = ADCResolution.ADCRES_12BIT_32S

    mode: Annotated[
        Mode,
        Field(
            default=Mode.SHUNT_AND_BUS_CONTINUOUS,
            title="Operating Mode",
            description="Operating mode setting for the sensor. Options include continuous and triggered modes.",
            examples=[Mode.SHUNT_AND_BUS_CONTINUOUS],
        ),
    ] = Mode.SHUNT_AND_BUS_CONTINUOUS

    current_lsb: Annotated[
        float,
        Field(
            ...,
            title="Current LSB (mA/bit)",
            description=(
                "Calibration parameter representing the current LSB "
                "in milliamps per bit (e.g., 0.1 mA per bit). Must be positive."
            ),
            examples=[0.1],
            gt=0,
        ),
    ] = 0.1

    calibration_value: Annotated[
        int,
        Field(
            ...,
            title="Calibration Value",
            description=(
                "Calibration register value (a magic number based on the shunt resistor). "
                "This should be a positive integer."
            ),
            examples=[4096],
            gt=0,
        ),
    ] = 4096

    power_lsb: Annotated[
        float,
        Field(
            ...,
            title="Power LSB (W/bit)",
            description=(
                "Calibration parameter representing the power LSB "
                "in watts per bit (e.g., 0.002 W per bit). Must be positive."
            ),
            examples=[0.002],
            gt=0,
        ),
    ] = 0.002


class ServoConfig(BaseModel):
    name: Annotated[
        str,
        Field(
            ...,
            description="A name for the servo (useful for debugging/logging). ",
            examples=["Steering Direction", "Camera Pan"],
        ),
    ]
    calibration_offset: Annotated[
        float,
        Field(
            0.0,
            description="A calibration offset for fine-tuning servo angles.",
            examples=[0.0, 0.4, -4.2],
        ),
    ]
    min_angle: Annotated[
        int,
        Field(
            ...,
            description="Minimum allowable angle for the servo",
            examples=[-30, -45],
        ),
    ]
    max_angle: Annotated[
        int,
        Field(
            ...,
            description="Maximum allowable angle for the servo",
            examples=[30, 45],
        ),
    ]
    min_pulse: Annotated[
        int,
        Field(
            ...,
            description="The pulse width in microseconds (µs) corresponding to the servo's minimum position",
            examples=[500],
        ),
    ] = 500

    max_pulse: Annotated[
        int,
        Field(
            ...,
            description="The maximum pulse width in microseconds (µs) corresponding to the servo's maximum position.",
            examples=[2500],
        ),
    ] = 2500

    calibration_mode: Annotated[
        ServoCalibrationMode,
        Field(
            ...,
            title="Calibration mode",
            description="Specifies how calibration offsets are applied.",
            examples=[
                ServoCalibrationMode.SUM.value,
                ServoCalibrationMode.NEGATIVE.value,
            ],
        ),
    ] = ServoCalibrationMode.NEGATIVE

    @model_validator(mode="after")
    def validate_servo_config(self):
        """
        Ensure logical consistency in servo configuration:
        - min_angle should be less than max_angle
        - calibration_offset should be within a reasonable range (-360 to 360)
        """
        logger.info("self.min_angle=%s", self.min_angle)

        if self.min_angle >= self.max_angle:
            raise ValueError(
                f"`min_angle` must be less than `max_angle` for {self.name}."
            )
        if not -360 <= self.calibration_offset <= 360:
            raise ValueError(
                f"Calibration offset {self.calibration_offset} for {self.name} must be in the range [-360, 360]."
            )
        return self


class AngularServoConfig(ServoConfig):
    enabled: EnabledField = True
    channel: Annotated[
        Union[str, int],
        Field(
            ...,
            title="PWM channel",
            json_schema_extra={"type": "string_or_number"},
            description="PWM channel number or name.",
            examples=["P0", "P1", "P2", 0, 1, 2],
        ),
    ]
    driver: Annotated[
        PWMDriverConfig,
        Field(
            ...,
            title="PWM driver",
            description="The PWM driver chip configuration.",
        ),
    ] = PWMDriverConfig()


class GPIOAngularServoConfig(ServoConfig):
    enabled: EnabledField = True
    pin: Annotated[
        Union[str, int],
        Field(
            ...,
            json_schema_extra={"type": "string_or_number"},
            title="GPIO PIN",
            description="The GPIO PIN that the servo is connected to",
            examples=["GPIO2", "GPIO3", 0, 1, 2],
        ),
    ]


class MotorBaseConfig(BaseModel):
    enabled: EnabledField = True
    name: Annotated[
        str,
        Field(
            ...,
            title="Name",
            description="Human-readable name for the motor",
            examples=["left", "right"],
        ),
    ]
    calibration_direction: MotorDirectionField
    max_speed: Annotated[
        int,
        Field(
            ...,
            title="Max speed",
            description="Maximum allowable speed for the motor.",
            examples=[100, 90],
        ),
    ]

    @model_validator(mode="after")
    def validate_motor_config(self):
        """
        Ensure logical consistency in motor configuration:
        - max_speed should be a positive integer.
        - calibration_direction should be either 1 or -1.
        """
        if self.max_speed <= 0:
            raise ValueError(
                f"`max_speed` must be greater than 0 for motor '{self.name}'."
            )
        if self.calibration_direction not in [1, -1]:
            raise ValueError(
                f"`calibration_direction` for motor '{self.name}' must be either 1 or -1."
            )
        return self


class HBridgeMotorConfig(MotorBaseConfig):
    """
    HBridgeMotor is used when you want to control the motor using an external or
    abstracted PWM driver (often over I²C).
    """

    driver: Annotated[
        PWMDriverConfig,
        Field(
            ...,
            title="PWM driver",
            description="The PWM driver chip configuration.",
        ),
    ] = PWMDriverConfig()

    channel: Annotated[
        Union[str, int],
        Field(
            ...,
            title="PWM channel",
            json_schema_extra={"type": "string_or_number"},
            description="PWM channel number or name.",
            examples=["P0", "P1", "P2", 0, 1, 2],
        ),
    ] = "P0"

    dir_pin: Annotated[
        Union[str, int],
        Field(
            ...,
            title="Direction (phase) pin",
            json_schema_extra={"type": "string_or_number"},
            description="The GPIO pin that the phase (direction) input of the motor driver chip is connected to.",
            examples=["D4", "D5", 23, 24],
        ),
    ]


class DCMotorConfig(MotorBaseConfig):
    """
    The DCMotor class is intended for cases where a motor is controlled directly via
    GPIO pins.

    It is suitable when the motor driver board (e.g., a Waveshare/MC33886-based module)
    does not require or use an external PWM driver and is controlled entirely through
    direct GPIO calls.

    """

    pwm: Annotated[
        bool,
        Field(
            ...,
            title="PWM",
            description="Whether to construct PWM Output Device instances for "
            "the motor controller pins, allowing both direction and speed control.",
        ),
    ] = True
    forward_pin: Annotated[
        Union[int, str],
        Field(
            ...,
            title="Forward PIN",
            description="The GPIO pin that the forward input of the motor driver chip "
            "is connected to.",
        ),
    ]
    backward_pin: Annotated[
        Union[int, str],
        Field(
            ...,
            json_schema_extra={"type": "string_or_number"},
            title="Backward PIN",
            description="The GPIO pin that the forward input of the motor driver chip "
            "is connected to.",
        ),
    ]
    enable_pin: Annotated[
        Optional[Union[int, str]],
        Field(
            ...,
            title="Enable PIN",
            json_schema_extra={"type": "string_or_number"},
            description="The GPIO pin that enables the motor. "
            "Required for **some** motor controller boards.",
        ),
    ] = None


class LedConfig(BaseModel):
    """
    A model to represent the LED configuration.
    """

    name: Annotated[
        Optional[str],
        Field(
            ...,
            description="Human-readable name",
            examples=["LED"],
        ),
    ] = None

    pin: Annotated[
        Union[str, int],
        Field(
            default=26,
            json_schema_extra={"type": "string_or_number"},
            description="The GPIO pin number for the LED.",
            examples=[26, "D14"],
        ),
    ]

    interval: Annotated[
        float,
        Field(
            default=0.1,
            ge=0,
            description="The interval of LED blinking.",
            json_schema_extra={"type": "string_or_number"},
            examples=[
                0.1,
            ],
        ),
    ]


class UPS_S3Config(AddressModel):
    driver_type: Annotated[
        Literal["INA219"],
        Field(..., title="Driver type", frozen=True),
    ] = "INA219"
    config: Annotated[
        INA219Config,
        Field(
            ...,
            title="INA219 config",
            description="Configuration for INA219",
        ),
    ] = INA219Config()
    address: AddressField = 0x41

    bus: Annotated[
        int,
        Field(
            ...,
            title="The I2C bus",
            description="I2C bus number",
            examples=[1, 4],
            ge=0,
        ),
    ] = 1


class SunfounderBatteryConfig(AddressModel):
    driver_type: Annotated[
        Literal["Sunfounder"],
        Field(..., title="Driver type", frozen=True),
    ] = "Sunfounder"
    channel: Annotated[
        Union[str, int],
        Field(
            ...,
            json_schema_extra={"type": "string_or_number"},
            description="ADC channel number or name.",
            examples=["A4", 1, 3, 4],
        ),
    ] = "A4"

    address: AddressField = "0x14"

    bus: Annotated[
        int,
        Field(
            ...,
            title="The I2C bus",
            description="I2C bus number",
            examples=[1, 4],
            ge=0,
        ),
    ] = 1

    @field_validator("channel", mode="before")
    def parse_channel(cls, value):
        if (
            value not in ADC_ALLOWED_CHANNELS_PIN_NAMES
            and value not in ADC_ALLOWED_CHANNELS
        ):
            raise ValueError(ADC_ALLOWED_CHANNELS_DESCRIPTION)
        return value


class BatteryConfig(BaseModel):
    driver: Annotated[
        Union[SunfounderBatteryConfig, UPS_S3Config], Field(discriminator="driver_type")
    ] = SunfounderBatteryConfig()

    full_voltage: Annotated[
        float, Field(..., description="The maximum voltage.", examples=[8.4])
    ]
    warn_voltage: Annotated[
        float, Field(..., description="The warning voltage threshold.", examples=[7.15])
    ]
    danger_voltage: Annotated[
        float, Field(..., description="The danger voltage threshold.", examples=[6.5])
    ]
    min_voltage: Annotated[
        float, Field(..., description="The minimum voltage.", examples=[6.0])
    ]
    auto_measure_seconds: Annotated[
        int,
        Field(
            ...,
            ge=0,
            description="Time interval in seconds for automatic measurement.",
            examples=[60],
        ),
    ]
    cache_seconds: Annotated[
        float, Field(..., ge=0, description="Cache duration in seconds.", examples=[2])
    ]

    @model_validator(mode="after")
    def validate_voltage_levels(cls, model):
        if not (
            model.min_voltage
            < model.danger_voltage
            < model.warn_voltage
            < model.full_voltage
        ):
            raise ValueError(
                "Voltage levels must satisfy the condition: min_voltage < danger_voltage < warn_voltage < full_voltage"
            )
        return model


class HardwareConfig(BaseModel):
    """
    Configuration model for specifying motors and servos in a robotic system.
    """

    steering_servo: Annotated[
        Union[GPIOAngularServoConfig, AngularServoConfig, None],
        Field(
            ...,
            title="Steering Servo",
            description="Configuration for the steering servo.",
        ),
    ] = None
    cam_pan_servo: Annotated[
        Union[GPIOAngularServoConfig, AngularServoConfig, None],
        Field(
            ...,
            title="Camera Pan Servo",
            description="Configuration for the camera pan servo.",
        ),
    ] = None
    cam_tilt_servo: Annotated[
        Union[GPIOAngularServoConfig, AngularServoConfig, None],
        Field(
            ...,
            title="Camera Tilt Servo",
            description="Configuration for the camera tilt servo.",
        ),
    ] = None
    left_motor: Annotated[
        Union[DCMotorConfig, HBridgeMotorConfig, None],
        Field(
            ...,
            title="Left Motor",
            description="Configuration for the left motor.",
        ),
    ] = None
    right_motor: Annotated[
        Union[DCMotorConfig, HBridgeMotorConfig, None],
        Field(
            ...,
            title="Right Motor",
            description="Configuration for the right motor.",
        ),
    ] = None

    battery: Annotated[
        BatteryConfig,
        Field(
            ...,
            title="Battery",
            description="Configuration for the battery.",
        ),
    ]

    ultrasonic: Annotated[
        Union[UltrasonicConfig, None],
        Field(
            ...,
            title="Ultrasonic",
            description="Configuration for the ultrasonic.",
        ),
    ] = None

    led: Annotated[
        Optional[LedConfig],
        Field(
            ...,
            title="LED",
            description="Configuration for the LED.",
        ),
    ] = None


if __name__ == "__main__":
    import json

    with open("config-schema.json", "w") as f:
        json.dump(HardwareConfig.model_json_schema(), f, indent=2)
