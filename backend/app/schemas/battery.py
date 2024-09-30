from pydantic import BaseModel


class BatteryStatusResponse(BaseModel):
    """
    Schema for the battery status response.

    Attributes:
    - voltage: The voltage of the battery in volts, e.g. '7.8'.
    """

    voltage: float
