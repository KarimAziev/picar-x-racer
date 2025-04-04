"""
Endpoints related to synchronizing settings between the main application and the robot application.
"""

from typing import TYPE_CHECKING, Annotated

from app.api import robot_deps
from app.schemas.settings import Settings
from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from app.services.control.car_service import CarService
    from app.services.sensors.battery_service import BatteryService

router = APIRouter()


@router.post(
    "/px/api/settings/refresh",
    response_model=Settings,
    summary="Reload settings for dependent services.",
)
async def update_settings(
    new_settings: Settings,
    battery_manager: Annotated[
        "BatteryService", Depends(robot_deps.get_battery_service)
    ],
    robot_service: Annotated["CarService", Depends(robot_deps.get_battery_service)],
):
    """
    Reload settings for dependent services.
    """
    robot_service.app_settings = new_settings

    if new_settings.battery:
        battery_manager.update_battery_settings(new_settings.battery)

    return new_settings
