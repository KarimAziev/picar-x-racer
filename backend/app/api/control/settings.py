"""
Endpoints with robot-specific settings and calibration.
"""

from typing import Annotated, Any, Dict

from app.api import robot_deps
from app.core.px_logger import Logger
from app.managers.file_management.json_data_manager import JsonDataManager
from app.schemas.calibration import CalibrationConfig
from app.schemas.config import HardwareConfig
from app.util.doc_util import build_response_description
from fastapi import APIRouter, Depends

router = APIRouter()

_log = Logger(name=__name__)


@router.get(
    "/px/api/settings/json-schema",
    response_model=Dict[str, Any],
    summary="Retrieve JSON schema of hardware configuration fields. ",
    responses={
        200: {
            "description": "A JSON schema with extra properties for UI.",
            "content": {
                "application/json": {"example": HardwareConfig.model_json_schema()}
            },
        },
    },
)
def get_json_schema():
    """
    Retrieve the a JSON-like schema representation of robot config settings.

    Used for dynamic rendering of corresponding settings on the UI.
    """
    return HardwareConfig.model_json_schema()


@router.get(
    "/px/api/settings/config",
    response_model=HardwareConfig,
    summary="Retrieve the saved or default robot configuration",
    response_description=build_response_description(
        HardwareConfig, "Successful response with the robot configuration."
    ),
)
def get_config_settings(
    config_manager: Annotated[
        "JsonDataManager", Depends(robot_deps.get_config_manager)
    ],
):
    """
    Retrieve currently saved or default robot configuration.
    """
    _log.debug("Retrieving robot config settings")
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
    _log.debug("Retrieving robot calibration settings")
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
