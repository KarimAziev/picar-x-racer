from pydantic import BaseModel, Field


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
