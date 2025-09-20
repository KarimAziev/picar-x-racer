"""
Endpoints with robot-specific settings and calibration.
"""

import asyncio
from typing import Annotated, Any, Dict

from app.api import robot_deps
from app.core.px_logger import Logger
from app.exceptions.settings import InvalidSettings, UnchangedSettings
from app.managers.file_management.json_data_manager import JsonDataManager
from app.schemas.robot.calibration import CalibrationConfig
from app.schemas.robot.config import HardwareConfig, PartialHardwareConfig
from app.services.connection_service import ConnectionService
from app.services.control.settings_service import SettingsService
from app.util.doc_util import build_response_description
from fastapi import APIRouter, Depends, HTTPException

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


@router.put(
    "/px/api/settings/config",
    response_model=HardwareConfig,
    summary="Update robot settings.",
    response_description=build_response_description(
        HardwareConfig, "Successful response with the robot configuration."
    ),
)
async def update_settings(
    settings: HardwareConfig,
    settings_service: Annotated[
        "SettingsService", Depends(robot_deps.get_robot_settings_service)
    ],
    connection_manager: Annotated[
        "ConnectionService", Depends(robot_deps.get_connection_manager)
    ],
):
    """
    Update robot settings.
    """
    _log.info("Saving robot hardware settings")
    data = await asyncio.to_thread(settings_service.save_settings, settings)
    await connection_manager.broadcast_json(
        {"payload": data.model_dump(mode="json"), "type": "robot_settings"}
    )
    return data


@router.patch(
    "/px/api/settings/config",
    response_model=PartialHardwareConfig,
    summary="Merge partial robot settings.",
    response_description=build_response_description(
        PartialHardwareConfig,
        "Successful response with the partial robot configuration.",
    ),
)
async def merge_partial_settings(
    settings: PartialHardwareConfig,
    settings_service: Annotated[
        "SettingsService", Depends(robot_deps.get_robot_settings_service)
    ],
    connection_manager: Annotated[
        "ConnectionService", Depends(robot_deps.get_connection_manager)
    ],
):
    """
    Merge partial robot settings with saved configuration.
    """
    _log.info("Saving partial robot hardware settings")

    try:
        partial_settings = await asyncio.to_thread(
            settings_service.merge_settings, settings
        )
    except (UnchangedSettings, InvalidSettings) as err:
        err_msg = str(err)
        _log.error(err_msg)
        raise HTTPException(status_code=409, detail=err_msg)
    except Exception:
        _log.error("Unhandled error during merging settings", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    await connection_manager.broadcast_json(
        {
            "payload": partial_settings.model_dump(mode="json", exclude_unset=True),
            "type": "robot_partial_settings",
        }
    )
    return partial_settings


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
