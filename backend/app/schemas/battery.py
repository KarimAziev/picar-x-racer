from typing import List, Optional

from pydantic import BaseModel, Field


class BatteryStatusResponse(BaseModel):
    """
    Schema for the battery status response.
    """

    name: str = Field(..., description="Configured name of the monitored supply.")

    voltage: Optional[float] = Field(
        None,
        description="The current voltage of the battery in volts.",
        examples=[7.1, 6.42],
    )

    current: Optional[float] = Field(
        None,
        description=(
            "Current draw in amps, or null when the configured sensor does not "
            "support current measurement."
        ),
        examples=[1.25, 0.42],
    )

    percentage: Optional[float] = Field(
        None,
        description=(
            "The remaining battery charge as a percentage. This value is calculated based on the current "
            "voltage relative to the battery's configured minimum and full voltage levels. A value of 0% "
            "indicates the voltage is at or below the minimum, and 100% indicates it is at the full voltage."
        ),
        examples=[61.1, 23.3],
    )

    error: Optional[str] = Field(
        None, description="Sensor-specific read or initialization error."
    )


BatteryStatusListResponse = List[BatteryStatusResponse]
