import asyncio
from typing import TYPE_CHECKING

from app.api import deps
from app.schemas.config import CalibrationConfig, ConfigSchema
from app.schemas.settings import Settings, SettingsUpdateRequest
from app.util.logger import Logger
from fastapi import APIRouter, Depends, Request

if TYPE_CHECKING:
    from app.services.battery_service import BatteryService
    from app.services.connection_service import ConnectionService
    from app.services.file_service import FileService

logger = Logger(__name__)

router = APIRouter()


@router.get("/settings", response_model=Settings)
def get_settings(file_service: "FileService" = Depends(deps.get_file_manager)):
    """
    Retrieve the current application settings.

    Args:
    --------------
    - file_service (FileService): The file service for managing settings.

    Returns:
    --------------
    - `Settings`: The current settings of the application.
    """
    return file_service.load_settings()


@router.post("/settings", response_model=Settings)
async def update_settings(
    request: Request,
    new_settings: SettingsUpdateRequest,
    file_service: "FileService" = Depends(deps.get_file_manager),
    battery_manager: "BatteryService" = Depends(deps.get_battery_manager),
):
    """
    Update the application settings.
    Returns:
    --------------
    - `Settings`: The updated settings of the application.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager

    if new_settings.battery:
        battery_manager.update_battery_settings(new_settings.battery)

    data = new_settings.model_dump(exclude_unset=True)
    logger.info("Settings update data %s", data)

    await asyncio.to_thread(file_service.save_settings, data)

    await connection_manager.broadcast_json({"type": "settings", "payload": data})

    return new_settings


@router.get("/settings/config", response_model=ConfigSchema)
def get_config_settings(
    file_service: "FileService" = Depends(deps.get_file_manager),
):
    """
    Retrieve the calibration settings.

    Args:
    --------------
    - file_service (FileService): The file service for managing settings.

    Returns:
    --------------
    - `ConfigSchema`: The calibration settings.
    """
    return file_service.get_robot_config()


@router.get("/settings/calibration", response_model=CalibrationConfig)
def get_calibration_settings(
    file_service: "FileService" = Depends(deps.get_file_manager),
):
    """
    Retrieve the calibration settings.

    Args:
    --------------
    - file_service (FileService): The file service for managing settings.

    Returns:
    --------------
    - `CalibrationConfig`: The calibration settings.
    """
    return file_service.get_calibration_config()
