from pydantic import BaseModel


class BatteryStatusResponse(BaseModel):
    voltage: float
