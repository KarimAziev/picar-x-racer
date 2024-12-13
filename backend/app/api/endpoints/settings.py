import asyncio
from typing import TYPE_CHECKING

from app.api.deps import get_battery_manager, get_file_manager
from app.schemas.settings import CalibrationConfig, Settings
from app.util.logger import Logger
from fastapi import APIRouter, Depends, Request

if TYPE_CHECKING:
    from app.services.battery_service import BatteryService
    from app.services.connection_service import ConnectionService
    from app.services.files_service import FilesService

logger = Logger(__name__)

router = APIRouter()


@router.get("/api/settings", response_model=Settings)
def get_settings(file_service: "FilesService" = Depends(get_file_manager)):
    """
    Retrieve the current application settings.

    Args:
    --------------
    - file_service (FilesService): The file service for managing settings.

    Returns:
    --------------
    - `Settings`: The current settings of the application.
    """
    return file_service.load_settings()


@router.post("/api/settings", response_model=Settings)
async def update_settings(
    request: Request,
    new_settings: Settings,
    file_service: "FilesService" = Depends(get_file_manager),
    battery_manager: "BatteryService" = Depends(get_battery_manager),
):
    """
    Update the application settings.
    Returns:
    --------------
    - `Settings`: The updated settings of the application.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    data = new_settings.model_dump(exclude_unset=True)
    logger.info("Settings update data %s", data)

    await asyncio.to_thread(file_service.save_settings, data)

    await connection_manager.broadcast_json({"type": "settings", "payload": data})

    for key, value in data.items():
        if hasattr(battery_manager, key) and getattr(battery_manager, key) != value:
            setattr(battery_manager, key, value)

    return new_settings


@router.get("/api/settings/calibration", response_model=CalibrationConfig)
def get_calibration_settings(
    file_service: "FilesService" = Depends(get_file_manager),
):
    """
    Retrieve the calibration settings.

    Args:
    --------------
    - file_service (FilesService): The file service for managing settings.

    Returns:
    --------------
    - `CalibrationConfig`: The calibration settings.
    """
    return file_service.get_calibration_config()
