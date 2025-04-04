import app.api.control.battery as battery
import app.api.control.car_control as car_control
import app.api.control.settings as settings
import app.api.control.system as system
import app.api.control.ultrasonic as ultrasonic
from app.util.endpoints_metadata import build_routers_and_metadata
from fastapi import APIRouter

routers, tags_metadata = build_routers_and_metadata(
    [system, settings, car_control, battery, ultrasonic]
)

api_router = APIRouter()

for router in routers:
    api_router.include_router(router, tags=router.tags)

__all__ = ["api_router", "tags_metadata"]
