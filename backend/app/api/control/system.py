"""
Endpoints responsible for performing cleanup and shutdown operations for
robot-controlled hardware services.
These endpoints do not perform the underlying shutdown logic directly themselves;
rather, they trigger the cleanup methods of dependent services (battery, motor control,
distance sensing, etc.) that are part of the robot application.
"""

from typing import TYPE_CHECKING, Annotated

from app.api import robot_deps
from app.core.px_logger import Logger
from app.schemas.system import ShutdownResponse
from app.services.sensors.led_service import LEDService
from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from app.services.control.car_service import CarService
    from app.services.sensors.battery_service import BatteryService
    from app.services.sensors.distance_service import DistanceService

router = APIRouter()
logger = Logger(name=__name__)


@router.get(
    "/px/api/system/shutdown",
    response_model=ShutdownResponse,
    summary="Gracefully shut down robot services",
    response_description="Response indicating whether the robotic services have been gracefully shut down. "
    "When successful, the response will have 'success' set to True. "
    "If there are any issues during the shutdown process, 'success' will be False "
    "and 'errors' will include a list of error messages describing the encountered problems",
)
async def shutdown(
    battery_service: Annotated[
        "BatteryService", Depends(robot_deps.get_battery_service)
    ],
    robot_service: Annotated["CarService", Depends(robot_deps.get_robot_service)],
    distance_service: Annotated[
        "DistanceService", Depends(robot_deps.get_distance_service)
    ],
    led_service: Annotated["LEDService", Depends(robot_deps.get_led_service)],
):
    """
    Initiates a graceful shutdown of the robot application's core services.
    """
    errors = []
    try:
        logger.debug("Gracefully stopping battery service")
        await battery_service.cleanup_connection_manager()
    except Exception as e:
        errors.append(str(e))
        logger.error("Failed to cleanup battery service: %s", e)

    try:
        logger.debug("Gracefully stopping robot service")
        await robot_service.cleanup()
    except Exception as e:
        errors.append(str(e))
        logger.error("Failed to cleanup robot service: %s", e)

    try:
        logger.debug("Gracefully stopping distance service")
        await distance_service.cleanup()
    except Exception as e:
        logger.debug("Gracefully stopping distance service")
        errors.append(str(e))
        logger.error("Failed to cleanup distance service: %s", e)

    try:
        await led_service.cleanup()
    except Exception as e:
        errors.append(str(e))
        logger.error("Failed to cleanup LED service: %s", e)

    if errors:
        return {"errors": errors, "success": False}
    return {"success": True}
