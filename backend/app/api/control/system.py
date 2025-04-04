"""
Operations and endpoints related to system-level actions.
Note, it doesn't perform actions itself; rather, it makes cleanups for dependent services.
"""

from typing import TYPE_CHECKING, Annotated

from app.api import robot_deps
from app.core.logger import Logger
from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from app.services.control.car_service import CarService
    from app.services.sensors.battery_service import BatteryService
    from app.services.sensors.distance_service import DistanceService

router = APIRouter()
logger = Logger(__name__, app_name="px_robot")


@router.get(
    "/px/api/system/shutdown",
    summary="Attempt to gracefully shutdown robot services.",
)
async def shutdown(
    battery_service: Annotated[
        "BatteryService", Depends(robot_deps.get_battery_service)
    ],
    robot_service: Annotated["CarService", Depends(robot_deps.get_battery_service)],
    distance_service: Annotated[
        "DistanceService", Depends(robot_deps.get_distance_service)
    ],
):
    """
    Attempt to gracefully shutdown robot services.
    """
    try:
        await battery_service.cleanup_connection_manager()
    except Exception as e:
        logger.error("Failed to cleanup battery service: %s", e)

    try:
        await robot_service.cleanup()
    except Exception as e:
        logger.error("Failed to cleanup robot service: %s", e)

    try:
        await distance_service.cleanup()
    except Exception as e:
        logger.error("Failed to cleanup distance service: %s", e)
