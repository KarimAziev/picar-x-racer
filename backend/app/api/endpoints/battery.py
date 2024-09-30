from app.schemas.battery import BatteryStatusResponse
from app.util.get_battery_voltage import get_battery_voltage as read_battery_voltage
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/battery-status", response_model=BatteryStatusResponse)
def get_battery_voltage():
    """
    Read the ADC value and convert it to a voltage.

    This endpoint retrieves the current voltage of the battery by reading the ADC (Analog-to-Digital Converter) value and converting it to voltage.

    Returns:
        dict: A dictionary containing the measured voltage in volts.

    Example response:
    {
        "voltage": 7.8
    }
    """
    value: float = read_battery_voltage()
    return {"voltage": value}
