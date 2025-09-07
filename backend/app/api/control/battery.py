"""
Endpoints related to the battery monitoring.
"""

from typing import TYPE_CHECKING, Annotated

from app.api import robot_deps
from app.core.px_logger import Logger
from app.schemas.battery import BatteryStatusResponse
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.services.sensors.battery_service import BatteryService

router = APIRouter()
logger = Logger(name=__name__)


@router.get(
    "/px/api/battery-status",
    response_model=BatteryStatusResponse,
    summary="Retrieve the current battery status in volts and percentage.",
    response_description="An object containing measured voltage in volts, "
    "e.g., '7.1,' and the remaining battery charge as a percentage.",
)
async def get_battery_voltage(
    request: Request,
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
    battery_manager: "BatteryService" = request.app.state.battery_service
    logger.info("get battery voltage")
    (voltage, percentage) = await battery_manager.broadcast_state()
    logger.debug(
        "Retrieved battery status - Voltage: %sV, Percentage: %s", voltage, percentage
    )
    if voltage is not None:
        return {"voltage": voltage, "percentage": percentage}
    else:
        raise HTTPException(status_code=500, detail="Error reading voltage")
