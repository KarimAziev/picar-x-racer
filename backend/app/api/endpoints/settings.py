from typing import TYPE_CHECKING

from app.api.deps import get_file_manager
from app.config.detectors import detectors
from app.config.video_enhancers import frame_enhancers
from app.schemas.settings import (
    CalibrationConfig,
    DetectorsResponse,
    EnhancersResponse,
    Settings,
    VideoModesResponse,
)
from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from app.services.files_service import FilesService


router = APIRouter()


@router.get("/api/settings", response_model=Settings)
def get_settings(file_service: "FilesService" = Depends(get_file_manager)):
    """
    Retrieve the current application settings.

    Args:
    - file_service (FilesService): The file service for managing settings.

    Returns:
        `Settings`: The current settings of the application.
    """
    return file_service.load_settings()


@router.post("/api/settings", response_model=Settings)
def update_settings(
    new_settings: Settings,
    file_service: "FilesService" = Depends(get_file_manager),
):
    """
    Update the application settings.

    Args:
    - new_settings (Settings): The new settings to apply.
    - file_service (FilesService): The file service for managing settings.

    Returns:
        `Settings`: The updated settings of the application.
    """
    data = new_settings.model_dump(exclude_none=True, exclude_defaults=True)

    file_service.save_settings(data)
    return new_settings


@router.get("/api/calibration", response_model=CalibrationConfig)
def get_calibration_settings(
    file_service: "FilesService" = Depends(get_file_manager),
):
    """
    Retrieve the calibration settings.

    Args:
    - file_service (FilesService): The file service for managing settings.

    Returns:
        `CalibrationConfig`: The calibration settings.
    """
    return file_service.get_calibration_config()


@router.get("/api/detectors", response_model=DetectorsResponse)
def get_detectors():
    """
    Retrieve a list of available object detectors.

    Returns:
        `DetectorsResponse`: A list of available detector names.
    """
    return {"detectors": list(detectors.keys())}


@router.get("/api/enhancers", response_model=EnhancersResponse)
def get_frame_enhancers():
    """
    Retrieve a list of available frame enhancers.

    Returns:
        `EnhancersResponse`: A list of available frame enhancer names.
    """
    return {"enhancers": list(frame_enhancers.keys())}


@router.get("/api/video-modes", response_model=VideoModesResponse)
def get_video_modes():
    """
    Retrieve a list of available video modes, including both detectors and enhancers.

    Returns:
        `VideoModesResponse`: A list of available detector and enhancer names.
    """
    return {
        "detectors": list(detectors.keys()),
        "enhancers": list(frame_enhancers.keys()),
    }
