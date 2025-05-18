import re
from typing import Literal, Optional, Union

from app.core.logger import Logger
from app.schemas.distance import UltrasonicConfig
from pydantic import (
    BaseModel,
    Field,
    WithJsonSchema,
    computed_field,
    field_validator,
    model_validator,
)
from robot_hat import MotorDirection, ServoCalibrationMode
from robot_hat.data_types.config.motor import (
    GPIODCMotorConfig as GPIODCMotorConfigDataclass,
)
from robot_hat.data_types.config.motor import (
    I2CDCMotorConfig as I2CDCMotorConfigDataclass,
)
from robot_hat.data_types.config.motor import (
    PhaseMotorConfig as PhaseMotorConfigDataclass,
)
from robot_hat.data_types.config.pwm import PWMDriverConfig as PWMDriverConfigDataclass
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
        json_schema_extra={"type": "motor_direction"},
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

ina219_adc_resolutions_options = [
    {
        "value": ADCResolution.ADCRES_9BIT_1S,
        "label": "9-bit, 1 sample, 84µs",
    },
    {
        "value": ADCResolution.ADCRES_10BIT_1S,
        "label": "10-bit, 1 sample, 148µs",
    },
    {
        "value": ADCResolution.ADCRES_11BIT_1S,
        "label": "11-bit, 1 sample, 276µs",
    },
    {
        "value": ADCResolution.ADCRES_12BIT_1S,
        "label": "12-bit, 1 sample, 532µs",
    },
    {
        "value": ADCResolution.ADCRES_12BIT_2S,
        "label": "12-bit, 2 samples, 1.06ms",
    },
    {
        "value": ADCResolution.ADCRES_12BIT_4S,
        "label": "12-bit, 4 samples, 2.13ms",
    },
    {
        "value": ADCResolution.ADCRES_12BIT_8S,
        "label": "12-bit, 8 samples, 4.26ms",
    },
    {
        "value": ADCResolution.ADCRES_12BIT_16S,
        "label": "12-bit, 16 samples, 8.51ms",
    },
    {
        "value": ADCResolution.ADCRES_12BIT_32S,
        "label": "12-bit, 32 samples, 17.02ms",
    },
    {
        "value": ADCResolution.ADCRES_12BIT_64S,
        "label": "12-bit, 64 samples, 34.05ms",
    },
    {
        "value": ADCResolution.ADCRES_12BIT_128S,
        "label": "12-bit, 128 samples, 68.10ms",
    },
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
    The configuration parameters to control a PWM driver chip via the I2C bus.
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
            description="The I2C bus number used to communicate with the PWM driver chip. ",
            examples=[1, 4],
            ge=0,
        ),
    ] = 1
    frame_width: Annotated[
        int,
        Field(
            ...,
            title="Frame Width in µs",
            description="Determines the full cycle duration between servo control pulses in microseconds. "
            "This value represents the period in which all servo channels are refreshed. "
            "A typical servo expects a pulse every 20000 µs (20 ms), and altering this value can affect "
            "the overall responsiveness and timing sensitivity of the servo's control signal.",
            examples=[20000],
            ge=1,
        ),
    ] = 20000
    freq: Annotated[
        int,
        Field(
            ...,
            title="PWM frequency (Hz)",
            description="The PWM frequency in Hertz which controls the granularity of the pulse width modulation. "
            "Higher frequencies allow for more precise adjustments of the pulse width (duty cycle), "
            "resulting in smoother and more accurate servo movements. Conversely, lower frequencies might lead "
            "to coarser control.",
            examples=[50],
            gt=0,
        ),
    ] = 50

    address: AddressField = "0x40"

    def to_dataclass(self) -> PWMDriverConfigDataclass:
        return PWMDriverConfigDataclass(
            address=self.addr_int,
            name=self.name,
            bus=self.bus,
            frame_width=self.frame_width,
            freq=self.freq,
        )


class INA219Config(BaseModel):
    """
    The configuration parameters for the INA219 digital current sensor.

    This configuration includes settings that determine the sensor's voltage range, gain (which governs
    the sensitivity of the shunt voltage measurement), and ADC resolution for both the bus and shunt voltage
    channels.

    """

    bus_voltage_range: Annotated[
        BusVoltageRange,
        Field(
            {
                "title": "Bus Voltage Range",
                "type": "select",
                "description": "Defines the maximum voltage range measurable by the sensor. "
                "Options must match your circuit design to avoid over-range measurements (e.g., 16V or 32V).",
                "json_schema_extra": {
                    "type": "select",
                    "props": {
                        "options": [
                            {"value": BusVoltageRange.RANGE_16V, "label": "16V"},
                            {"value": BusVoltageRange.RANGE_32V, "label": "32V"},
                        ],
                    },
                },
                "examples": [BusVoltageRange.RANGE_32V, BusVoltageRange.RANGE_16V],
            }
        ),
    ] = BusVoltageRange.RANGE_32V

    gain: Annotated[
        Gain,
        WithJsonSchema(
            {
                "title": "Gain Setting",
                "description": (
                    "Gain setting for the shunt voltage measurement, "
                    "affecting the sensor's sensitivity to small voltage drops."
                ),
                "type": "select",
                "props": {
                    "options": [
                        {"value": Gain.DIV_1_40MV, "label": "1x gain, 40mV range"},
                        {"value": Gain.DIV_2_80MV, "label": "2x gain, 80mV range"},
                        {
                            "value": Gain.DIV_4_160MV,
                            "label": "4x gain, 160mV range",
                        },
                        {
                            "value": Gain.DIV_8_320MV,
                            "label": "8x gain, 320mV range",
                        },
                    ]
                },
                "examples": [Gain.DIV_8_320MV],
            }
        ),
    ] = Gain.DIV_8_320MV

    bus_adc_resolution: Annotated[
        ADCResolution,
        WithJsonSchema(
            {
                "title": "Bus ADC Resolution",
                "type": "select",
                "props": {
                    "options": [
                        {
                            "value": ADCResolution.ADCRES_9BIT_1S,
                            "label": "9-bit, 1 sample, 84µs",
                        },
                        {
                            "value": ADCResolution.ADCRES_10BIT_1S,
                            "label": "10-bit, 1 sample, 148µs",
                        },
                        {
                            "value": ADCResolution.ADCRES_11BIT_1S,
                            "label": "11-bit, 1 sample, 276µs",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_1S,
                            "label": "12-bit, 1 sample, 532µs",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_2S,
                            "label": "12-bit, 2 samples, 1.06ms",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_4S,
                            "label": "12-bit, 4 samples, 2.13ms",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_8S,
                            "label": "12-bit, 8 samples, 4.26ms",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_16S,
                            "label": "12-bit, 16 samples, 8.51ms",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_32S,
                            "label": "12-bit, 32 samples, 17.02ms",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_64S,
                            "label": "12-bit, 64 samples, 34.05ms",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_128S,
                            "label": "12-bit, 128 samples, 68.10ms",
                        },
                    ],
                },
                "description": "The ADC resolution and averaging for bus voltage measurements. "
                "A higher resolution improves voltage accuracy but may affect sampling speed.",
                "examples": [ADCResolution.ADCRES_12BIT_32S],
            },
        ),
    ] = ADCResolution.ADCRES_12BIT_32S

    shunt_adc_resolution: Annotated[
        ADCResolution,
        WithJsonSchema(
            {
                "title": "Shunt ADC Resolution",
                "description": "The ADC resolution and averaging for shunt voltage measurements. "
                "Higher resolution settings result in more precise current conversion.",
                "examples": [ADCResolution.ADCRES_12BIT_32S],
                "type": "select",
                "props": {
                    "options": [
                        {
                            "value": ADCResolution.ADCRES_9BIT_1S,
                            "label": "9-bit, 1 sample, 84µs",
                        },
                        {
                            "value": ADCResolution.ADCRES_10BIT_1S,
                            "label": "10-bit, 1 sample, 148µs",
                        },
                        {
                            "value": ADCResolution.ADCRES_11BIT_1S,
                            "label": "11-bit, 1 sample, 276µs",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_1S,
                            "label": "12-bit, 1 sample, 532µs",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_2S,
                            "label": "12-bit, 2 samples, 1.06ms",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_4S,
                            "label": "12-bit, 4 samples, 2.13ms",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_8S,
                            "label": "12-bit, 8 samples, 4.26ms",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_16S,
                            "label": "12-bit, 16 samples, 8.51ms",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_32S,
                            "label": "12-bit, 32 samples, 17.02ms",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_64S,
                            "label": "12-bit, 64 samples, 34.05ms",
                        },
                        {
                            "value": ADCResolution.ADCRES_12BIT_128S,
                            "label": "12-bit, 128 samples, 68.10ms",
                        },
                    ]
                },
            }
        ),
    ] = ADCResolution.ADCRES_12BIT_32S

    mode: Annotated[
        Mode,
        WithJsonSchema(
            {
                "title": "Operating Mode",
                "description": "Operating mode for the sensor (e.g., continuous measurement for "
                "both bus and shunt voltages) to balance between immediate responsiveness and "
                "power efficiency.",
                "examples": [Mode.SHUNT_AND_BUS_CONTINUOUS],
                "type": "select",
                "props": {
                    "options": [
                        {"value": Mode.POWERDOWN, "label": "POWERDOWN"},
                        {
                            "value": Mode.SHUNT_VOLT_TRIGGERED,
                            "label": "SHUNT_VOLT_TRIGGERED",
                        },
                        {
                            "value": Mode.BUS_VOLT_TRIGGERED,
                            "label": "BUS_VOLT_TRIGGERED",
                        },
                        {
                            "value": Mode.SHUNT_AND_BUS_TRIGGERED,
                            "label": "SHUNT_AND_BUS_TRIGGERED",
                        },
                        {"value": Mode.ADC_OFF, "label": "ADC_OFF"},
                        {
                            "value": Mode.SHUNT_VOLT_CONTINUOUS,
                            "label": "SHUNT_VOLT_CONTINUOUS",
                        },
                        {
                            "value": Mode.BUS_VOLT_CONTINUOUS,
                            "label": "BUS_VOLT_CONTINUOUS",
                        },
                        {
                            "value": Mode.SHUNT_AND_BUS_CONTINUOUS,
                            "label": "SHUNT_AND_BUS_CONTINUOUS",
                        },
                    ]
                },
            }
        ),
    ] = Mode.SHUNT_AND_BUS_CONTINUOUS

    current_lsb: Annotated[
        float,
        Field(
            ...,
            title="Current LSB (mA/bit)",
            description="The conversion factor that translates the raw ADC reading "
            "of the shunt voltage into a current measurement (in mA). "
            "A smaller value increases measurement resolution, "
            "which is crucial for detecting low currents accurately.",
            examples=[0.1],
            gt=0,
        ),
    ] = 0.1

    calibration_value: Annotated[
        int,
        Field(
            ...,
            title="Calibration Value",
            description="The calibration register value computed based on "
            "the shunt resistor characteristics and the expected maximum current. ",
            examples=[4096],
            gt=0,
        ),
    ] = 4096

    power_lsb: Annotated[
        float,
        Field(
            ...,
            title="Power LSB (W/bit)",
            description="The conversion factor from the raw power register output into watts. "
            "Derived from the current_lsb, it ensures that the calculated power "
            "from the measured current and bus voltage is consistent with physical measurements.",
            examples=[0.002],
            gt=0,
            json_schema_extra={
                "props": {
                    "step": 0.001,
                    "minFractionDigits": 0,
                    "maxFractionDigits": 6,
                },
            },
        ),
    ] = 0.002


class ServoConfig(BaseModel):
    enabled: EnabledField = True
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
    ] = -30
    max_angle: Annotated[
        int,
        Field(
            ...,
            description="Maximum allowable angle for the servo",
            examples=[30, 45],
        ),
    ] = 30
    dec_step: Annotated[
        int,
        Field(
            ...,
            description="The step value by which the servo's angle decreases. Must be a negative integer.",
            examples=[-5, -10],
            lt=0,
        ),
    ] = -5
    inc_step: Annotated[
        int,
        Field(
            ...,
            description="The step value by which the servo's angle increases. Must be a positive integer.",
            gt=0,
            examples=[5, 2],
        ),
    ] = 5
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
            json_schema_extra={
                "tooltipHelp": "Specifies how calibration offsets are applied.",
                "title": "Calibration mode",
            },
        ),
    ] = ServoCalibrationMode.NEGATIVE

    @model_validator(mode="after")
    def validate_servo_config(self):
        """
        Ensure logical consistency in servo configuration:
        - min_angle should be less than max_angle
        - calibration_offset should be within a reasonable range (-360 to 360)
        """

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
    """Configuration for servos driven via external PWM driver or HAT via I²C."""

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
    """
    Configuration for servos driven directly via Raspberry Pi GPIO (without I²C and external PWM driver).
    """

    pin: Annotated[
        Union[str, int],
        Field(
            ...,
            json_schema_extra={"type": "string_or_number"},
            title="GPIO PIN",
            description="Broadcom (BCM) pin number for the GPIO pins, as opposed to physical (BOARD) numbering.",
            examples=["GPIO17", "GPIO27", 1, 2],
        ),
    ]


class MotorBaseConfig(BaseModel):
    enabled: EnabledField = True
    calibration_direction: MotorDirectionField
    name: Annotated[
        str,
        Field(
            ...,
            title="Name",
            description="Human-readable name for the motor",
            examples=["left", "right"],
        ),
    ]
    max_speed: Annotated[
        int,
        Field(
            ...,
            title="Max speed",
            description="Maximum allowable speed for the motor.",
            examples=[100, 90],
            gt=0,
        ),
    ]

    @model_validator(mode="after")
    def validate_motor_config(self):
        """
        Ensure logical consistency in motor configuration:
        - calibration_direction should be either 1 or -1.
        """
        if self.calibration_direction not in [1, -1]:
            raise ValueError(
                f"`calibration_direction` for motor '{self.name}' must be either 1 or -1."
            )
        return self


class I2CDCMotorConfig(MotorBaseConfig):
    """
    The configuration for the motor, which is controlled via a PWM driver over I²C.
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

    def to_dataclass(self) -> I2CDCMotorConfigDataclass:
        return I2CDCMotorConfigDataclass(
            calibration_direction=self.calibration_direction,
            name=self.name,
            max_speed=self.max_speed,
            driver=self.driver.to_dataclass(),
            channel=self.channel,
            dir_pin=self.dir_pin,
        )


class GPIODCMotorConfig(MotorBaseConfig):
    """
    The configuration for the motor, which is controlled without I²C.

    It is suitable when the motor driver board, for example, a Waveshare/MC33886-based
    module, does not require or use an external PWM driver and is controlled entirely
    through direct GPIO calls.
    """

    forward_pin: Annotated[
        Union[int, str],
        Field(
            ...,
            title="Forward PIN",
            json_schema_extra={"type": "string_or_number"},
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
    pwm: Annotated[
        bool,
        Field(
            ...,
            title="PWM",
            description="Whether to construct PWM Output Device instances for "
            "the motor controller pins, allowing both direction and speed control.",
        ),
    ] = True

    def to_dataclass(self) -> GPIODCMotorConfigDataclass:
        return GPIODCMotorConfigDataclass(
            calibration_direction=self.calibration_direction,
            name=self.name,
            max_speed=self.max_speed,
            forward_pin=self.forward_pin,
            backward_pin=self.backward_pin,
            enable_pin=self.enable_pin,
            pwm=self.pwm,
        )


class PhaseMotorConfig(MotorBaseConfig):
    """
    The configuration for the a phase/enable motor driver board.
    """

    phase_pin: Annotated[
        Union[int, str],
        Field(
            ...,
            title="Enable PIN",
            json_schema_extra={"type": "string_or_number"},
            description="GPIO pin for the phase/direction. ",
        ),
    ]
    pwm: Annotated[
        bool,
        Field(
            ...,
            title="PWM",
            description="Whether to construct PWM Output Device instances for "
            "the motor controller pins, allowing both direction and speed control.",
        ),
    ] = True

    enable_pin: Annotated[
        Union[int, str],
        Field(
            ...,
            title="Enable PIN",
            json_schema_extra={"type": "string_or_number"},
            description="The GPIO pin that enables the motor. "
            "Required for **some** motor controller boards.",
        ),
    ]

    def to_dataclass(self) -> PhaseMotorConfigDataclass:
        return PhaseMotorConfigDataclass(
            calibration_direction=self.calibration_direction,
            name=self.name,
            max_speed=self.max_speed,
            phase_pin=self.phase_pin,
            pwm=self.pwm,
            enable_pin=self.enable_pin,
        )


class LedConfig(BaseModel):
    """
    The configuration for the single LED.
    """

    name: Annotated[
        str,
        Field(
            ...,
            description="Human-readable name",
            examples=["LED"],
        ),
    ] = "LED"

    interval: Annotated[
        float,
        Field(
            default=0.1,
            ge=0,
            description="The interval of LED blinking.",
            json_schema_extra={
                "props": {
                    "step": 0.1,
                    "minFractionDigits": 0,
                    "maxFractionDigits": 6,
                    "placeholder": "Interval (in seconds)",
                },
            },
            examples=[
                0.1,
            ],
        ),
    ]

    pin: Annotated[
        Union[str, int],
        Field(
            default=26,
            json_schema_extra={"type": "string_or_number"},
            description="The GPIO pin number for the LED.",
            examples=[26],
        ),
    ]


class INA219BatteryDriverConfig(AddressModel):
    """
    The settings for configuring an INA219-based current and voltage sensor driver (e.g.
    the UPS Module 3S from Waveshare).
    """

    driver_type: Annotated[
        Literal["INA219"],
        Field(..., title="Driver type", frozen=True),
    ] = "INA219"
    config: Annotated[
        INA219Config,
        Field(
            ...,
            title="INA219 config",
            description="The configuration parameters for the INA219 digital current sensor.",
        ),
    ] = INA219Config()
    address: AddressField = 0x41

    bus: Annotated[
        int,
        Field(
            ...,
            title="The I2C bus",
            description="The I2C bus number used to communicate with the driver chip. ",
            examples=[1, 4],
            ge=0,
        ),
    ] = 1


class SunfounderBatteryConfig(AddressModel):
    """
    The settings for configuring battery and power monitoring for Sunfounder's Robot HAT.
    """

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
    """
    The settings for configuring battery and power monitoring.
    """

    enabled: EnabledField = True

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

    driver: Annotated[
        Union[SunfounderBatteryConfig, INA219BatteryDriverConfig],
        Field(discriminator="driver_type"),
    ] = SunfounderBatteryConfig()

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
    The configuration for the robot components and sensors.
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
        Union[GPIODCMotorConfig, I2CDCMotorConfig, PhaseMotorConfig, None],
        Field(
            ...,
            title="Left Motor",
            description="Configuration for the left motor.",
        ),
    ] = None
    right_motor: Annotated[
        Union[GPIODCMotorConfig, I2CDCMotorConfig, PhaseMotorConfig, None],
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
            title="Distance sensor",
            description="Configuration for the distance sensor.",
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
