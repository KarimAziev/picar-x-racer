"""
Endpoints to retrieve and update various application settings.
"""

import asyncio
from typing import TYPE_CHECKING, Any, Dict

from app.api import deps
from app.core.logger import Logger
from app.schemas.config import CalibrationConfig, ConfigSchema
from app.schemas.settings import Settings, SettingsUpdateRequest
from app.util.doc_util import build_response_description
from app.util.pydantic_helpers import schema_to_dynamic_json
from fastapi import APIRouter, Depends, Request

if TYPE_CHECKING:
    from app.services.battery_service import BatteryService
    from app.services.connection_service import ConnectionService
    from app.services.file_service import FileService

logger = Logger(__name__)

router = APIRouter()


@router.get(
    "/settings",
    response_model=Settings,
    summary="Retrieve application-wide configuration",
    response_description=build_response_description(
        Settings, "Successful response with current settings."
    ),
)
def get_settings(file_service: "FileService" = Depends(deps.get_file_manager)):
    """
    Retrieve the current application settings.
    """
    return file_service.load_settings()


@router.post(
    "/settings",
    response_model=Settings,
    summary="Update current application settings",
    response_description=build_response_description(
        Settings, "Successful response with an all application-wide settings."
    ),
)
async def update_settings(
    request: Request,
    new_settings: SettingsUpdateRequest,
    file_service: "FileService" = Depends(deps.get_file_manager),
    battery_manager: "BatteryService" = Depends(deps.get_battery_manager),
):
    """
    Update the application settings.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager

    if new_settings.battery:
        battery_manager.update_battery_settings(new_settings.battery)

    data = new_settings.model_dump(exclude_unset=True)

    logger.info("Updating settings with %s", data)

    await asyncio.to_thread(file_service.save_settings, data)

    await connection_manager.broadcast_json({"type": "settings", "payload": data})

    return new_settings


@router.get(
    "/settings/config",
    response_model=ConfigSchema,
    summary="Retrieve current config",
    response_description=build_response_description(
        ConfigSchema, "Successful response with the robot configuration."
    ),
)
def get_config_settings(
    file_service: "FileService" = Depends(deps.get_file_manager),
):
    """
    Retrieve the robot config.
    """
    return file_service.get_robot_config()


@router.get("/settings/robot-fields", response_model=Dict[str, Any])
def get_fields_config():
    """
    Retrieve the a JSON-like schema representation of robot config settings.
    """
    return schema_to_dynamic_json(ConfigSchema)


@router.get("/settings/calibration", response_model=CalibrationConfig)
def get_calibration_settings(
    file_service: "FileService" = Depends(deps.get_file_manager),
):
    """
    Retrieve the calibration settings.
    """
    return file_service.get_calibration_config()
