"""
Endpoints to synchronize configuration settings from the main application to the robot
application.
Typically, when settings changes occur in the main app, this endpoint is invoked by an
integration service (e.g., via HTTP) to update the internal configuration of
robot-dependent services.
"""

from typing import TYPE_CHECKING, Annotated, Any, Dict

from app.api import robot_deps
from app.core.px_logger import Logger
from app.managers.file_management.json_data_manager import JsonDataManager
from app.schemas.config import CalibrationConfig, ConfigSchema
from app.schemas.settings import Settings
from app.util.doc_util import build_response_description
from app.util.pydantic_helpers import schema_to_dynamic_json
from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from app.services.control.car_service import CarService
    from app.services.sensors.battery_service import BatteryService

router = APIRouter()

logger = Logger(name=__name__)


@router.post(
    "/px/api/settings/update",
    response_model=Settings,
    summary="Reload settings for dependent services.",
)
async def update_settings(
    new_settings: Settings,
    battery_manager: Annotated[
        "BatteryService", Depends(robot_deps.get_battery_service)
    ],
    robot_service: Annotated["CarService", Depends(robot_deps.get_robot_service)],
):
    """
    Reload settings for dependent services.
    """
    robot_service.app_settings = new_settings

    logger.debug("Updating robot app settings")

    if new_settings.battery:
        logger.debug("Updating battery settings")
        battery_manager.update_battery_settings(new_settings.battery)

    return new_settings


@router.get(
    "/px/api/settings/robot-fields",
    response_model=Dict[str, Any],
    summary="Retrieve current robot configuration",
)
def get_fields_config():
    """
    Retrieve the a JSON-like schema representation of robot config settings.
    """
    return schema_to_dynamic_json(ConfigSchema)


@router.get(
    "/px/api/settings/config",
    response_model=ConfigSchema,
    summary="Retrieve current robot configuration",
    response_description=build_response_description(
        ConfigSchema, "Successful response with the robot configuration."
    ),
)
def get_config_settings(
    config_manager: Annotated[
        "JsonDataManager", Depends(robot_deps.get_config_manager)
    ],
):
    """
    Retrieve the robot config.
    """
    logger.debug("Retrieving robot config settings")
    data = config_manager.load_data()
    return data


@router.get(
    "/px/api/settings/calibration",
    response_model=CalibrationConfig,
    summary="Retrieve saved (or default) calibration settings.",
)
def get_calibration_settings(
    config_manager: Annotated[
        "JsonDataManager", Depends(robot_deps.get_config_manager)
    ],
):
    """
    Retrieve saved calibration settings.
    """
    logger.debug("Retrieving robot calibration settings")
    config = config_manager.load_data()
    return {
        "steering_servo_offset": config.get("steering_servo", {}).get(
            "calibration_offset"
        ),
        "cam_tilt_servo_offset": config.get("cam_tilt_servo", {}).get(
            "calibration_offset"
        ),
        "cam_pan_servo_offset": config.get("cam_pan_servo", {}).get(
            "calibration_offset"
        ),
        "left_motor_direction": config.get("left_motor", {}).get(
            "calibration_direction"
        ),
        "right_motor_direction": config.get("right_motor", {}).get(
            "calibration_direction"
        ),
    }
