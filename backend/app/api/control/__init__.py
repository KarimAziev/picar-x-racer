import app.api.control.battery as battery
import app.api.control.auxiliary_sensors as auxiliary_sensors
import app.api.control.autonomy as autonomy
import app.api.control.car_control as car_control
import app.api.control.distance as distance
import app.api.control.integration as integration
import app.api.control.pinout as pinout
import app.api.control.settings as settings
import app.api.control.sensors as sensors
import app.api.control.system as system
from app.util.endpoints_metadata import build_routers_and_metadata
from fastapi import APIRouter

routers, tags_metadata = build_routers_and_metadata(
    [
        system,
        auxiliary_sensors,
        settings,
        car_control,
        autonomy,
        battery,
        distance,
        integration,
        pinout,
        sensors,
    ]
)

api_router = APIRouter()

for router in routers:
    api_router.include_router(router, tags=router.tags)

__all__ = ["api_router", "tags_metadata"]
