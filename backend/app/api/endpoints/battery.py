from typing import TYPE_CHECKING, Optional

from app.api.deps import get_battery_manager
from app.schemas.battery import BatteryStatusResponse
from fastapi import APIRouter, Depends, HTTPException

if TYPE_CHECKING:
    from app.services.battery_service import BatteryService

router = APIRouter()


@router.get(
    "/api/battery-status",
    response_model=BatteryStatusResponse,
    summary="Retrieve the current battery status in volts.",
)
async def get_battery_voltage(
    battery_manager: "BatteryService" = Depends(get_battery_manager),
):
    """
    Read the ADC value and convert it to a voltage.

    This endpoint retrieves the current voltage of the battery by reading the
    ADC (Analog-to-Digital Converter) value and converting it to voltage.

    Returns:
    --------------
    A dictionary containing the measured voltage in volts.

    Example response:
    --------------
    ```
    {
        "voltage": 7.8
    }
    ```
    """
    value: Optional[float] = await battery_manager.broadcast_state()
    if value is not None:
        return {"voltage": value}
    else:
        raise HTTPException(status_code=500, detail="Error reading voltage")
