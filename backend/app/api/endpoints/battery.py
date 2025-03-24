"""
Endpoints related to battery status and monitoring.
"""

from typing import TYPE_CHECKING

from app.api.deps import get_battery_service
from app.schemas.battery import BatteryStatusResponse
from fastapi import APIRouter, Depends, HTTPException

if TYPE_CHECKING:
    from app.services.sensors.battery_service import BatteryService

router = APIRouter()


@router.get(
    "/battery-status",
    response_model=BatteryStatusResponse,
    summary="Retrieve the current battery status in volts.",
)
async def get_battery_voltage(
    battery_manager: "BatteryService" = Depends(get_battery_service),
):
    """
    Read the ADC (Analog-to-Digital Converter) value and convert it to a voltage.

    Platform behavior:
    - On a Raspberry Pi, the function uses the actual hardware ADC (Analog-to-Digital Converter) interface.
    - On other platforms (e.g., local development or testing), it uses a mock ADC implementation.

    Returns:
    --------------
    A measured voltage in volts, e.g., '7.1,' and the remaining battery charge as a percentage, e.g., 61.1%.

    The percentage is calculated based on the voltage relative to the battery's
    configured minimum and full voltage levels.

    A value of 0% indicates the voltage is at or below the minimum,
    and 100% indicates it is at the full voltage.
    """
    (voltage, percentage) = await battery_manager.broadcast_state()
    if voltage is not None:
        return {"voltage": voltage, "percentage": percentage}
    else:
        raise HTTPException(status_code=500, detail="Error reading voltage")
