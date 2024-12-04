import asyncio
from typing import TYPE_CHECKING

from app.schemas.battery import BatteryStatusResponse
from app.util.get_battery_voltage import get_battery_voltage as read_battery_voltage
from fastapi import APIRouter, Request

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService

router = APIRouter()


@router.get(
    "/api/battery-status",
    response_model=BatteryStatusResponse,
    summary="Retrieve the current battery status in volts.",
)
async def get_battery_voltage(request: Request):
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
    connection_manager: "ConnectionService" = request.app.state.app_manager
    value: float = await asyncio.to_thread(read_battery_voltage)
    await connection_manager.broadcast_json({"type": "battery", "payload": value})
    return {"voltage": value}
