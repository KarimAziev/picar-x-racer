"""
Endpoints responsible for performing cleanup and shutdown operations for
robot-controlled hardware services.
These endpoints do not perform the underlying shutdown logic directly themselves;
rather, they trigger the cleanup methods of dependent services (battery, motor control,
distance sensing, etc.) that are part of the robot application.
"""

from typing import TYPE_CHECKING, Annotated, Optional

from app.api import robot_deps
from app.core.px_logger import Logger
from app.schemas.system import ShutdownResponse
from app.services.sensors.led_service import LEDService
from fastapi import APIRouter, Depends, Request

if TYPE_CHECKING:
    from app.services.control.car_service import CarService
    from app.services.sensors.battery_service import BatteryService
    from app.services.sensors.distance_service import DistanceService
    from app.services.autonomy.sensor_publishers import LocalizationSensorService
    from app.services.autonomy.lidar_safety import LidarSafetyService
    from app.services.autonomy.local_mapping import LocalMappingService

router = APIRouter()
_log = Logger(name=__name__)


@router.post(
    "/px/api/system/shutdown",
    response_model=ShutdownResponse,
    summary="Gracefully shut down robot services",
    response_description="Response indicating whether the robotic services have been gracefully shut down. "
    "When successful, the response will have 'success' set to True. "
    "If there are any issues during the shutdown process, 'success' will be False "
    "and 'errors' will include a list of error messages describing the encountered problems",
)
async def shutdown(
    request: Request,
    robot_service: Annotated["CarService", Depends(robot_deps.get_robot_service)],
    distance_service: Annotated[
        "DistanceService", Depends(robot_deps.get_distance_service)
    ],
    led_service: Annotated["LEDService", Depends(robot_deps.get_led_service)],
    sensor_service: Annotated[
        "LocalizationSensorService",
        Depends(robot_deps.get_localization_sensor_service),
    ],
    lidar_safety_service: Annotated[
        Optional["LidarSafetyService"],
        Depends(robot_deps.get_lidar_safety_service),
    ],
    local_mapping_service: Annotated[
        Optional["LocalMappingService"],
        Depends(robot_deps.get_local_mapping_service),
    ],
):
    """
    Initiates a graceful shutdown of the robot application's core services.
    """
    errors: list[str] = []
    battery_service: "BatteryService" = request.app.state.battery_service
    try:
        _log.debug("Gracefully stopping battery service")
        await battery_service.cleanup_connection_manager()
    except Exception as e:
        errors.append(str(e))
        _log.error("Failed to cleanup battery service: %s", e)

    try:
        _log.debug("Gracefully stopping robot service")
        await robot_service.cleanup()
    except Exception as e:
        errors.append(str(e))
        _log.error("Failed to cleanup robot service: %s", e)

    try:
        _log.debug("Gracefully stopping distance service")
        await distance_service.cleanup()
    except Exception as e:
        _log.debug("Gracefully stopping distance service")
        errors.append(str(e))
        _log.error("Failed to cleanup distance service: %s", e)

    try:
        await led_service.cleanup()
    except Exception as e:
        errors.append(str(e))
        _log.error("Failed to cleanup LED service: %s", e)

    try:
        await sensor_service.stop()
    except Exception as e:
        errors.append(str(e))
        _log.error("Failed to cleanup localization sensor service: %s", e)

    if local_mapping_service:
        try:
            await local_mapping_service.stop()
        except Exception as e:
            errors.append(str(e))
            _log.error("Failed to cleanup local mapping service: %s", e)

    if lidar_safety_service:
        try:
            await lidar_safety_service.stop()
        except Exception as e:
            errors.append(str(e))
            _log.error("Failed to cleanup LiDAR safety service: %s", e)

    if errors:
        return {"errors": errors, "success": False}
    return {"success": True}
