from typing import Literal, Union

from app.schemas.robot.common import AddressField, AddressModel, EnabledField
from pydantic import BaseModel, Field, WithJsonSchema, field_validator, model_validator
from robot_hat.drivers.adc.INA219 import ADCResolution, BusVoltageRange, Gain, Mode
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
        BusVoltageRange,
        WithJsonSchema(
            {
                "title": "Bus Voltage Range",
                "description": "Defines the maximum voltage range measurable by the sensor. "
                "Options must match your circuit design to avoid over-range measurements (e.g., 16V or 32V).",
                "type": "select",
                "props": {
                    "options": [
                        {"value": BusVoltageRange.RANGE_16V, "label": "16V"},
                        {"value": BusVoltageRange.RANGE_32V, "label": "32V"},
                    ],
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
    print("\n\033[1m\033[32m Battery config \033[0m\033[36mJSON schema:\033[0m")
    pp(BatteryConfig.model_json_schema())
