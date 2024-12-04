import asyncio
from typing import TYPE_CHECKING

from app.api.deps import get_camera_manager, get_detection_manager, get_file_manager
from app.schemas.settings import CalibrationConfig, Settings
from fastapi import APIRouter, Depends, Request

if TYPE_CHECKING:
    from app.services.camera_service import CameraService
    from app.services.connection_service import ConnectionService
    from app.services.detection_service import DetectionService
    from app.services.files_service import FilesService


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
    camera_manager: "CameraService" = Depends(get_camera_manager),
    detection_manager: "DetectionService" = Depends(get_detection_manager),
):
    """
    Update the application settings.

    Args:
    --------------
    - request (Request): The incoming HTTP request.
    - new_settings (Settings): The new settings to apply.
    - file_service (FilesService): The file service for managing settings.
    - camera_manager (CameraService): The camera service for managing the camera settings.
    - detection_manager (DetectionService): The detection service for managing the detection settings.


    Returns:
    --------------
    - `Settings`: The updated settings of the application.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    data = new_settings.model_dump(exclude_unset=True)

    await asyncio.to_thread(file_service.save_settings, data)

    await connection_manager.broadcast_json({"type": "settings", "payload": data})

    for key, value in data.items():
        if hasattr(camera_manager, key) and getattr(camera_manager, key) != value:
            setattr(camera_manager, key, value)
        elif (
            hasattr(detection_manager, key) and getattr(detection_manager, key) != value
        ):
            setattr(detection_manager, key, value)

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
