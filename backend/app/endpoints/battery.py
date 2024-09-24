from app.util.platform_adapters import get_battery_voltage as read_battery_voltage
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/api/battery-status")
def get_battery_voltage():
    value: float = read_battery_voltage()
    return JSONResponse(content={"voltage": value})
