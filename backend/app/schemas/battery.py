from pydantic import BaseModel, Field, model_validator


class BatteryStatusResponse(BaseModel):
    """
    Schema for the battery status response.

    Attributes:
    - voltage: The voltage of the battery in volts, e.g. '7.8'.
    """

    voltage: float = Field(
        ...,
        description="The voltage of the battery in volts, e.g. '7.8'",
        examples=[7.1, 6.4, 8.2],
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
    cache_seconds: int = Field(
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
