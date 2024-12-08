from pydantic import BaseModel, Field


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
