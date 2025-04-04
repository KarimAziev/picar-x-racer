"""
Endpoints to retrieve and update various application settings.
"""

import asyncio
import os
from typing import TYPE_CHECKING, Any, Dict

import httpx
from app.api import deps
from app.core.logger import Logger
from app.schemas.config import CalibrationConfig, ConfigSchema
from app.schemas.settings import Settings, SettingsUpdateRequest
from app.util.doc_util import build_response_description
from app.util.pydantic_helpers import schema_to_dynamic_json
from fastapi import APIRouter, Depends, Request

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.domain.settings_service import SettingsService

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
def get_settings(file_service: "SettingsService" = Depends(deps.get_settings_service)):
    """
    Retrieve the current application settings.
    """
    return file_service.load_settings()


@router.post(
    "/settings",
    response_model=Settings,
    summary="Update current application settings. Also refresh the settings in the robot app.",
    response_description=build_response_description(
        Settings, "Successful response with an all application-wide settings."
    ),
)
async def update_settings(
    request: Request,
    new_settings: SettingsUpdateRequest,
    file_service: "SettingsService" = Depends(deps.get_settings_service),
):
    """
    Update the application settings. Also refresh the settings in the robot app.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager

    data = new_settings.model_dump(exclude_unset=True)

    logger.info("Updating settings with %s", data)

    new_data = await asyncio.to_thread(file_service.save_settings, data)
    await connection_manager.broadcast_json({"type": "settings", "payload": data})

    control_port = os.getenv("PX_CONTROL_APP_PORT", "8001")
    robot_refresh_url = f"http://127.0.0.1:{control_port}/px/api/settings/refresh"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(robot_refresh_url, json=new_data)
            if response.status_code != 200:
                logger.error(
                    "Failed to refresh robot settings. Status code: %s, response: %s",
                    response.status_code,
                    response.text,
                )
    except Exception as exc:
        logger.error("Error calling robot app refresh endpoint: %s", exc)

    return new_data


@router.get(
    "/settings/config",
    response_model=ConfigSchema,
    summary="Retrieve current config",
    response_description=build_response_description(
        ConfigSchema, "Successful response with the robot configuration."
    ),
)
def get_config_settings(
    file_service: "SettingsService" = Depends(deps.get_settings_service),
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
    file_service: "SettingsService" = Depends(deps.get_settings_service),
):
    """
    Retrieve the calibration settings.
    """
    return file_service.get_calibration_config()
