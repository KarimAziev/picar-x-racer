from app.util.platform_adapters import get_battery_voltage as read_battery_voltage
from app.schemas.battery import BatteryStatusResponse
from fastapi import APIRouter

router = APIRouter()


@router.get("/api/battery-status", response_model=BatteryStatusResponse)
def get_battery_voltage():
    value: float = read_battery_voltage()
    return {"voltage": value}
