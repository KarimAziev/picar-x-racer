from pydantic import BaseModel, Field, model_validator


class BatteryStatusResponse(BaseModel):
    """
    Schema for the battery status response.
    """

    voltage: float = Field(
        ...,
        description="The current voltage of the battery in volts.",
        examples=[7.1, 6.42],
    )

    percentage: float = Field(
        ...,
        description=(
            "The remaining battery charge as a percentage. This value is calculated based on the current "
            "voltage relative to the battery's configured minimum and full voltage levels. A value of 0% "
            "indicates the voltage is at or below the minimum, and 100% indicates it is at the full voltage."
        ),
        examples=[61.1, 23.3],
    )


class BatterySettings(BaseModel):
    """
    Schema for the battery settings.
    """

    full_voltage: float = Field(..., description="The maximum voltage.", examples=[8.4])
    warn_voltage: float = Field(
        ..., description="The warning voltage threshold.", examples=[7.15]
    )
    danger_voltage: float = Field(
        ..., description="The danger voltage threshold.", examples=[6.5]
    )
    min_voltage: float = Field(..., description="The minimum voltage.", examples=[6.0])
    auto_measure_seconds: int = Field(
        ...,
        ge=0,
        description="Time interval in seconds for automatic measurement.",
        examples=[60],
    )
    cache_seconds: float = Field(
        ..., ge=0, description="Cache duration in seconds.", examples=[2]
    )

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
