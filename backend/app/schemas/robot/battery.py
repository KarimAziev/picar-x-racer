from typing import Literal, Optional, Union

from app.schemas.robot.common import AddressField, AddressModel, EnabledField, IC2Bus
from pydantic import BaseModel, Field, WithJsonSchema, field_validator, model_validator
from robot_hat import (
    INA219ADCResolution,
    INA219BusVoltageRange,
    INA219Gain,
    INA219Mode,
    INA226AvgMode,
    INA226ConversionTime,
    INA226Mode,
    INA260AveragingCount,
    INA260ConversionTime,
    INA260Mode,
)
from robot_hat import INA219Config as INA219DriverConfig
from robot_hat import INA226Config as INA226DriverConfig
from robot_hat import INA260Config as INA260DriverConfig
from robot_hat.drivers.adc.sunfounder_adc import (
    ADC_ALLOWED_CHANNELS,
    ADC_ALLOWED_CHANNELS_DESCRIPTION,
    ADC_ALLOWED_CHANNELS_PIN_NAMES,
)
from typing_extensions import Annotated


class INA219Config(BaseModel):
    """
    The configuration parameters for the INA219 digital current sensor.

    This configuration includes settings that determine the sensor's voltage range, gain (which governs
    the sensitivity of the shunt voltage measurement), and ADC resolution for both the bus and shunt voltage
    channels.

    """

    bus_voltage_range: Annotated[
        INA219BusVoltageRange,
        WithJsonSchema(
            {
                "title": "Bus Voltage Range",
                "description": "Defines the maximum voltage range measurable by the sensor. "
                "Options must match your circuit design to avoid over-range measurements (e.g., 16V or 32V).",
                "type": "select",
                "props": {
                    "options": [
                        {"value": INA219BusVoltageRange.RANGE_16V, "label": "16V"},
                        {"value": INA219BusVoltageRange.RANGE_32V, "label": "32V"},
                    ],
                },
                "examples": [
                    INA219BusVoltageRange.RANGE_32V,
                    INA219BusVoltageRange.RANGE_16V,
                ],
            }
        ),
    ] = INA219BusVoltageRange.RANGE_32V

    gain: Annotated[
        INA219Gain,
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
                        {
                            "value": INA219Gain.DIV_1_40MV,
                            "label": "1x gain, 40mV range",
                        },
                        {
                            "value": INA219Gain.DIV_2_80MV,
                            "label": "2x gain, 80mV range",
                        },
                        {
                            "value": INA219Gain.DIV_4_160MV,
                            "label": "4x gain, 160mV range",
                        },
                        {
                            "value": INA219Gain.DIV_8_320MV,
                            "label": "8x gain, 320mV range",
                        },
                    ]
                },
                "examples": [INA219Gain.DIV_8_320MV],
            }
        ),
    ] = INA219Gain.DIV_8_320MV

    bus_adc_resolution: Annotated[
        INA219ADCResolution,
        WithJsonSchema(
            {
                "title": "Bus ADC Resolution",
                "type": "select",
                "props": {
                    "options": [
                        {
                            "value": INA219ADCResolution.ADCRES_9BIT_1S,
                            "label": "9-bit, 1 sample, 84µs",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_10BIT_1S,
                            "label": "10-bit, 1 sample, 148µs",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_11BIT_1S,
                            "label": "11-bit, 1 sample, 276µs",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_1S,
                            "label": "12-bit, 1 sample, 532µs",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_2S,
                            "label": "12-bit, 2 samples, 1.06ms",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_4S,
                            "label": "12-bit, 4 samples, 2.13ms",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_8S,
                            "label": "12-bit, 8 samples, 4.26ms",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_16S,
                            "label": "12-bit, 16 samples, 8.51ms",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_32S,
                            "label": "12-bit, 32 samples, 17.02ms",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_64S,
                            "label": "12-bit, 64 samples, 34.05ms",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_128S,
                            "label": "12-bit, 128 samples, 68.10ms",
                        },
                    ],
                },
                "description": "The ADC resolution and averaging for bus voltage measurements. "
                "A higher resolution improves voltage accuracy but may affect sampling speed.",
                "examples": [INA219ADCResolution.ADCRES_12BIT_32S],
            },
        ),
    ] = INA219ADCResolution.ADCRES_12BIT_32S

    shunt_adc_resolution: Annotated[
        INA219ADCResolution,
        WithJsonSchema(
            {
                "title": "Shunt ADC Resolution",
                "description": "The ADC resolution and averaging for shunt voltage measurements. "
                "Higher resolution settings result in more precise current conversion.",
                "examples": [INA219ADCResolution.ADCRES_12BIT_32S],
                "type": "select",
                "props": {
                    "options": [
                        {
                            "value": INA219ADCResolution.ADCRES_9BIT_1S,
                            "label": "9-bit, 1 sample, 84µs",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_10BIT_1S,
                            "label": "10-bit, 1 sample, 148µs",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_11BIT_1S,
                            "label": "11-bit, 1 sample, 276µs",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_1S,
                            "label": "12-bit, 1 sample, 532µs",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_2S,
                            "label": "12-bit, 2 samples, 1.06ms",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_4S,
                            "label": "12-bit, 4 samples, 2.13ms",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_8S,
                            "label": "12-bit, 8 samples, 4.26ms",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_16S,
                            "label": "12-bit, 16 samples, 8.51ms",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_32S,
                            "label": "12-bit, 32 samples, 17.02ms",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_64S,
                            "label": "12-bit, 64 samples, 34.05ms",
                        },
                        {
                            "value": INA219ADCResolution.ADCRES_12BIT_128S,
                            "label": "12-bit, 128 samples, 68.10ms",
                        },
                    ]
                },
            }
        ),
    ] = INA219ADCResolution.ADCRES_12BIT_32S

    mode: Annotated[
        INA219Mode,
        WithJsonSchema(
            {
                "title": "Operating Mode",
                "description": "Operating mode for the sensor (e.g., continuous measurement for "
                "both bus and shunt voltages) to balance between immediate responsiveness and "
                "power efficiency.",
                "examples": [INA219Mode.SHUNT_AND_BUS_CONTINUOUS],
                "type": "select",
                "props": {
                    "options": [
                        {"value": INA219Mode.POWERDOWN, "label": "POWERDOWN"},
                        {
                            "value": INA219Mode.SHUNT_VOLT_TRIGGERED,
                            "label": "SHUNT_VOLT_TRIGGERED",
                        },
                        {
                            "value": INA219Mode.BUS_VOLT_TRIGGERED,
                            "label": "BUS_VOLT_TRIGGERED",
                        },
                        {
                            "value": INA219Mode.SHUNT_AND_BUS_TRIGGERED,
                            "label": "SHUNT_AND_BUS_TRIGGERED",
                        },
                        {"value": INA219Mode.ADC_OFF, "label": "ADC_OFF"},
                        {
                            "value": INA219Mode.SHUNT_VOLT_CONTINUOUS,
                            "label": "SHUNT_VOLT_CONTINUOUS",
                        },
                        {
                            "value": INA219Mode.BUS_VOLT_CONTINUOUS,
                            "label": "BUS_VOLT_CONTINUOUS",
                        },
                        {
                            "value": INA219Mode.SHUNT_AND_BUS_CONTINUOUS,
                            "label": "SHUNT_AND_BUS_CONTINUOUS",
                        },
                    ]
                },
            }
        ),
    ] = INA219Mode.SHUNT_AND_BUS_CONTINUOUS

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
    address: AddressField = "0x41"

    bus: IC2Bus = 1

    def to_dataclass(self) -> INA219DriverConfig:
        """Convert to the robot_hat INA219DriverConfig dataclass."""
        return INA219DriverConfig(
            bus_voltage_range=self.config.bus_voltage_range,
            gain=self.config.gain,
            bus_adc_resolution=self.config.bus_adc_resolution,
            shunt_adc_resolution=self.config.shunt_adc_resolution,
            mode=self.config.mode,
            current_lsb=self.config.current_lsb,
            calibration_value=self.config.calibration_value,
            power_lsb=self.config.power_lsb,
        )


DEFAULT_INA260_CONFIG = INA260DriverConfig()

INA260_AVERAGING_OPTIONS = [
    {"value": INA260AveragingCount.COUNT_1, "label": "1 sample"},
    {"value": INA260AveragingCount.COUNT_4, "label": "4 samples"},
    {"value": INA260AveragingCount.COUNT_16, "label": "16 samples"},
    {"value": INA260AveragingCount.COUNT_64, "label": "64 samples"},
    {"value": INA260AveragingCount.COUNT_128, "label": "128 samples"},
    {"value": INA260AveragingCount.COUNT_256, "label": "256 samples"},
    {"value": INA260AveragingCount.COUNT_512, "label": "512 samples"},
    {"value": INA260AveragingCount.COUNT_1024, "label": "1024 samples"},
]

INA260_CONVERSION_TIME_OPTIONS = [
    {"value": INA260ConversionTime.TIME_140_US, "label": "140µs"},
    {"value": INA260ConversionTime.TIME_204_US, "label": "204µs"},
    {"value": INA260ConversionTime.TIME_332_US, "label": "332µs"},
    {"value": INA260ConversionTime.TIME_588_US, "label": "588µs"},
    {"value": INA260ConversionTime.TIME_1_1_MS, "label": "1.1ms"},
    {"value": INA260ConversionTime.TIME_2_116_MS, "label": "2.116ms"},
    {"value": INA260ConversionTime.TIME_4_156_MS, "label": "4.156ms"},
    {"value": INA260ConversionTime.TIME_8_244_MS, "label": "8.244ms"},
]

INA260_MODE_OPTIONS = [
    {"value": INA260Mode.SHUTDOWN, "label": "Shutdown"},
    {"value": INA260Mode.CURRENT_TRIGGERED, "label": "Current triggered"},
    {"value": INA260Mode.BUS_TRIGGERED, "label": "Bus triggered"},
    {
        "value": INA260Mode.SHUNT_AND_BUS_TRIGGERED,
        "label": "Shunt + bus triggered",
    },
    {"value": INA260Mode.POWER_DOWN_4, "label": "Power down"},
    {
        "value": INA260Mode.CURRENT_CONTINUOUS,
        "label": "Current continuous",
    },
    {"value": INA260Mode.BUS_CONTINUOUS, "label": "Bus continuous"},
    {"value": INA260Mode.CONTINUOUS, "label": "Shunt + bus continuous"},
]


class INA260Config(BaseModel):
    """Extended configuration for the INA260 integrated current and voltage monitor."""

    averaging_count: Annotated[
        INA260AveragingCount,
        WithJsonSchema(
            {
                "title": "Averaging count",
                "description": "Number of samples included in the rolling conversion average.",
                "type": "select",
                "props": {"options": INA260_AVERAGING_OPTIONS},
                "examples": [DEFAULT_INA260_CONFIG.averaging_count],
            }
        ),
    ] = DEFAULT_INA260_CONFIG.averaging_count

    voltage_conversion_time: Annotated[
        INA260ConversionTime,
        WithJsonSchema(
            {
                "title": "Bus conversion time",
                "description": "Conversion interval for bus voltage measurements. Longer windows improve noise rejection.",
                "type": "select",
                "props": {"options": INA260_CONVERSION_TIME_OPTIONS},
                "examples": [DEFAULT_INA260_CONFIG.voltage_conversion_time],
            }
        ),
    ] = DEFAULT_INA260_CONFIG.voltage_conversion_time

    current_conversion_time: Annotated[
        INA260ConversionTime,
        WithJsonSchema(
            {
                "title": "Current conversion time",
                "description": "Conversion interval for shunt current measurements. Longer windows improve precision at the cost of speed.",
                "type": "select",
                "props": {"options": INA260_CONVERSION_TIME_OPTIONS},
                "examples": [DEFAULT_INA260_CONFIG.current_conversion_time],
            }
        ),
    ] = DEFAULT_INA260_CONFIG.current_conversion_time

    mode: Annotated[
        INA260Mode,
        WithJsonSchema(
            {
                "title": "Operating mode",
                "description": "Measurement mode controlling how the shunt and bus channels are sampled.",
                "type": "select",
                "props": {"options": INA260_MODE_OPTIONS},
                "examples": [DEFAULT_INA260_CONFIG.mode],
            }
        ),
    ] = DEFAULT_INA260_CONFIG.mode

    alert_mask: Annotated[
        int,
        Field(
            ...,
            title="Alert mask",
            description="Bitmask written to the mask/enable register (0-65535).",
            ge=0,
            le=0xFFFF,
            examples=[DEFAULT_INA260_CONFIG.alert_mask],
        ),
    ] = DEFAULT_INA260_CONFIG.alert_mask

    alert_limit: Annotated[
        int,
        Field(
            ...,
            title="Alert limit",
            description="Threshold register programmed for alert reporting (0-65535).",
            ge=0,
            le=0xFFFF,
            examples=[DEFAULT_INA260_CONFIG.alert_limit],
        ),
    ] = DEFAULT_INA260_CONFIG.alert_limit

    shunt_resistance_ohms: Annotated[
        float,
        Field(
            ...,
            title="Shunt resistance (Ω)",
            description="Effective shunt resistance used to derive current from measured voltage.",
            gt=0,
            le=0.01,
            examples=[DEFAULT_INA260_CONFIG.shunt_resistance_ohms],
            json_schema_extra={
                "props": {
                    "step": 0.0001,
                    "minFractionDigits": 0,
                    "maxFractionDigits": 6,
                }
            },
        ),
    ] = DEFAULT_INA260_CONFIG.shunt_resistance_ohms

    reset_on_init: Annotated[
        bool,
        Field(
            ...,
            title="Reset on init",
            description="Set the RESET bit before applying the configuration to force sensor defaults.",
            examples=[DEFAULT_INA260_CONFIG.reset_on_init],
        ),
    ] = DEFAULT_INA260_CONFIG.reset_on_init

    def to_dataclass(self) -> INA260DriverConfig:
        """Convert this Pydantic model to the underlying robot_hat dataclass."""

        return INA260DriverConfig(
            averaging_count=self.averaging_count,
            voltage_conversion_time=self.voltage_conversion_time,
            current_conversion_time=self.current_conversion_time,
            mode=self.mode,
            alert_mask=self.alert_mask,
            alert_limit=self.alert_limit,
            shunt_resistance_ohms=self.shunt_resistance_ohms,
            reset_on_init=self.reset_on_init,
        )


class INA260BatteryDriverConfig(AddressModel):
    """Configuration wrapper for an INA260-based voltage and current sensor."""

    driver_type: Annotated[
        Literal["INA260"],
        Field(..., title="Driver type", frozen=True),
    ] = "INA260"
    config: Annotated[
        INA260Config,
        Field(
            ...,
            title="INA260 config",
            description="Parameters for the INA260 integrated sensor.",
        ),
    ] = INA260Config()
    address: AddressField = "0x40"

    bus: IC2Bus = 1

    def to_dataclass(self) -> INA260DriverConfig:
        """Convert to the robot_hat INA260Config dataclass."""

        return self.config.to_dataclass()


DEFAULT_INA226_CONFIG = INA226DriverConfig.from_shunt(
    shunt_ohms=0.002,
    max_expected_amps=3.0,
    avg_mode=INA226AvgMode.AVG_16,
    bus_conv_time=INA226ConversionTime.CT_8244US,
    shunt_conv_time=INA226ConversionTime.CT_8244US,
    mode=INA226Mode.SHUNT_AND_BUS_CONT,
)

INA226_AVG_MODE_OPTIONS = [
    {"value": INA226AvgMode.AVG_1, "label": "1 sample"},
    {"value": INA226AvgMode.AVG_4, "label": "4 samples"},
    {"value": INA226AvgMode.AVG_16, "label": "16 samples"},
    {"value": INA226AvgMode.AVG_64, "label": "64 samples"},
    {"value": INA226AvgMode.AVG_128, "label": "128 samples"},
    {"value": INA226AvgMode.AVG_256, "label": "256 samples"},
    {"value": INA226AvgMode.AVG_512, "label": "512 samples"},
    {"value": INA226AvgMode.AVG_1024, "label": "1024 samples"},
]

INA226_CONVERSION_TIME_OPTIONS = [
    {"value": INA226ConversionTime.CT_140US, "label": "140us"},
    {"value": INA226ConversionTime.CT_204US, "label": "204us"},
    {"value": INA226ConversionTime.CT_332US, "label": "332us"},
    {"value": INA226ConversionTime.CT_588US, "label": "588us"},
    {"value": INA226ConversionTime.CT_1100US, "label": "1.1ms"},
    {"value": INA226ConversionTime.CT_2116US, "label": "2.116ms"},
    {"value": INA226ConversionTime.CT_4156US, "label": "4.156ms"},
    {"value": INA226ConversionTime.CT_8244US, "label": "8.244ms"},
]

INA226_MODE_OPTIONS = [
    {"value": INA226Mode.POWERDOWN, "label": "POWERDOWN"},
    {"value": INA226Mode.SHUNT_TRIG, "label": "SHUNT_TRIG"},
    {"value": INA226Mode.BUS_TRIG, "label": "BUS_TRIG"},
    {"value": INA226Mode.SHUNT_AND_BUS_TRIG, "label": "SHUNT_AND_BUS_TRIG"},
    {"value": INA226Mode.ADC_OFF, "label": "ADC_OFF"},
    {"value": INA226Mode.SHUNT_CONT, "label": "SHUNT_CONT"},
    {"value": INA226Mode.BUS_CONT, "label": "BUS_CONT"},
    {"value": INA226Mode.SHUNT_AND_BUS_CONT, "label": "SHUNT_AND_BUS_CONT"},
]


class INA226Config(BaseModel):
    """Schema for configuring the INA226 digital current sensor."""

    avg_mode: Annotated[
        INA226AvgMode,
        WithJsonSchema(
            {
                "title": "Averaging Mode",
                "description": "Number of samples averaged per measurement to balance noise and responsiveness.",
                "type": "select",
                "props": {"options": INA226_AVG_MODE_OPTIONS},
                "examples": [INA226AvgMode.AVG_16],
            }
        ),
    ] = DEFAULT_INA226_CONFIG.avg_mode

    bus_conv_time: Annotated[
        INA226ConversionTime,
        WithJsonSchema(
            {
                "title": "Bus Conversion Time",
                "description": "Conversion time for the bus voltage measurement. Longer times improve accuracy.",
                "type": "select",
                "props": {"options": INA226_CONVERSION_TIME_OPTIONS},
                "examples": [INA226ConversionTime.CT_8244US],
            }
        ),
    ] = DEFAULT_INA226_CONFIG.bus_conv_time

    shunt_conv_time: Annotated[
        INA226ConversionTime,
        WithJsonSchema(
            {
                "title": "Shunt Conversion Time",
                "description": "Conversion time for the shunt voltage measurement. Increase to improve precision.",
                "type": "select",
                "props": {"options": INA226_CONVERSION_TIME_OPTIONS},
                "examples": [INA226ConversionTime.CT_8244US],
            }
        ),
    ] = DEFAULT_INA226_CONFIG.shunt_conv_time

    mode: Annotated[
        INA226Mode,
        WithJsonSchema(
            {
                "title": "Operating Mode",
                "description": "Sensor operating mode controlling shunt/bus measurement behaviour and power draw.",
                "type": "select",
                "props": {"options": INA226_MODE_OPTIONS},
                "examples": [INA226Mode.SHUNT_AND_BUS_CONT],
            }
        ),
    ] = DEFAULT_INA226_CONFIG.mode

    shunt_ohms: Annotated[
        float,
        Field(
            ...,
            title="Shunt Resistance (Ohms)",
            description="Resistance of the shunt in ohms used for current sensing.",
            gt=0,
            examples=[DEFAULT_INA226_CONFIG.shunt_ohms],
            json_schema_extra={
                "props": {
                    "step": 0.0001,
                    "minFractionDigits": 0,
                    "maxFractionDigits": 6,
                }
            },
        ),
    ] = DEFAULT_INA226_CONFIG.shunt_ohms

    max_expected_amps: Annotated[
        Optional[float],
        Field(
            ...,
            title="Expected Max Current (A)",
            description="Expected maximum current draw in amperes. Set to null to derive from shunt limits.",
            examples=[DEFAULT_INA226_CONFIG.max_expected_amps],
            json_schema_extra={"props": {"step": 0.1, "min": 0}},
        ),
    ] = DEFAULT_INA226_CONFIG.max_expected_amps

    current_lsb: Annotated[
        float,
        Field(
            ...,
            title="Current LSB (A/bit)",
            description="Scaling factor mapping raw current register values to amperes.",
            gt=0,
            examples=[DEFAULT_INA226_CONFIG.current_lsb],
            json_schema_extra={
                "props": {
                    "step": 1e-06,
                    "minFractionDigits": 0,
                    "maxFractionDigits": 9,
                }
            },
        ),
    ] = DEFAULT_INA226_CONFIG.current_lsb

    calibration_value: Annotated[
        int,
        Field(
            ...,
            title="Calibration Register",
            description="Value written to the INA226 calibration register.",
            gt=0,
            le=INA226DriverConfig.MAX_CALIBRATION,
            examples=[DEFAULT_INA226_CONFIG.calibration_value],
        ),
    ] = DEFAULT_INA226_CONFIG.calibration_value

    power_lsb: Annotated[
        float,
        Field(
            ...,
            title="Power LSB (W/bit)",
            description="Scaling factor mapping raw power register values to watts.",
            gt=0,
            examples=[DEFAULT_INA226_CONFIG.power_lsb],
            json_schema_extra={
                "props": {
                    "step": 1e-06,
                    "minFractionDigits": 0,
                    "maxFractionDigits": 9,
                }
            },
        ),
    ] = DEFAULT_INA226_CONFIG.power_lsb

    @field_validator("max_expected_amps")
    def validate_max_expected_amps(cls, value) -> Optional[float]:
        if value is not None and value <= 0:
            raise ValueError("max_expected_amps must be greater than 0 when provided.")
        return value


class INA226BatteryDriverConfig(AddressModel):
    """Configuration for an INA226-based current and voltage sensor."""

    driver_type: Annotated[
        Literal["INA226"],
        Field(..., title="Driver type", frozen=True),
    ] = "INA226"
    config: Annotated[
        INA226Config,
        Field(
            ...,
            title="INA226 config",
            description="The configuration parameters for the INA226 digital current sensor.",
        ),
    ] = INA226Config()
    address: AddressField = "0x40"

    bus: IC2Bus = 1

    def to_dataclass(self) -> INA226DriverConfig:
        """Convert to the robot_hat INA226DriverConfig dataclass."""
        return INA226DriverConfig(
            avg_mode=self.config.avg_mode,
            bus_conv_time=self.config.bus_conv_time,
            shunt_conv_time=self.config.shunt_conv_time,
            mode=self.config.mode,
            shunt_ohms=self.config.shunt_ohms,
            max_expected_amps=self.config.max_expected_amps,
            current_lsb=self.config.current_lsb,
            calibration_value=self.config.calibration_value,
            power_lsb=self.config.power_lsb,
        )


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

    bus: IC2Bus = 1

    @field_validator("channel", mode="before")
    def parse_channel(cls, value: Union[int, str]) -> Union[str, int]:
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

    enabled: EnabledField = False

    full_voltage: Annotated[
        float, Field(..., description="The maximum voltage.", examples=[8.4])
    ] = 8.4
    warn_voltage: Annotated[
        float, Field(..., description="The warning voltage threshold.", examples=[7.15])
    ] = 7.15
    danger_voltage: Annotated[
        float, Field(..., description="The danger voltage threshold.", examples=[6.5])
    ] = 6.5
    min_voltage: Annotated[
        float, Field(..., description="The minimum voltage.", examples=[6.0])
    ] = 6.0
    auto_measure_seconds: Annotated[
        int,
        Field(
            ...,
            ge=0,
            description="Time interval in seconds for automatic measurement.",
            examples=[60],
        ),
    ] = 60
    cache_seconds: Annotated[
        float, Field(..., ge=0, description="Cache duration in seconds.", examples=[2])
    ] = 2

    driver: Annotated[
        Union[
            SunfounderBatteryConfig,
            INA219BatteryDriverConfig,
            INA226BatteryDriverConfig,
            INA260BatteryDriverConfig,
        ],
        Field(discriminator="driver_type"),
    ] = SunfounderBatteryConfig()

    @model_validator(mode="after")
    def validate_voltage_levels(cls, model) -> "BatteryConfig":
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


if __name__ == "__main__":
    from pprint import pp

    print(
        "\n\033[1m\033[32m Sunfounder Battery Config \033[0m\033[36mJSON schema:\033[0m"
    )
    pp(SunfounderBatteryConfig.model_json_schema())
    print(
        "\n\033[1m\033[32m INA219 Battery Driver Config \033[0m\033[36mJSON schema:\033[0m"
    )
    pp(INA219BatteryDriverConfig.model_json_schema())
    print(
        "\n\033[1m\033[32m INA226 Battery Driver Config \033[0m\033[36mJSON schema:\033[0m"
    )
    pp(INA226BatteryDriverConfig.model_json_schema())
    print(
        "\n\033[1m\033[32m INA260 Battery Driver Config \033[0m\033[36mJSON schema:\033[0m"
    )
    pp(INA260BatteryDriverConfig.model_json_schema())
    print("\n\033[1m\033[32m Battery config \033[0m\033[36mJSON schema:\033[0m")
    pp(BatteryConfig.model_json_schema())
