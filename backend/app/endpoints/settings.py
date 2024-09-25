from typing import TYPE_CHECKING

from app.config.detectors import detectors
from app.config.video_enhancers import frame_enhancers
from app.deps import get_file_manager
from app.schemas.settings import (
    CalibrationConfig,
    DetectorsResponse,
    EnhancersResponse,
    Settings,
    VideoModesResponse,
)
from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from app.controllers.files_controller import FilesController


router = APIRouter()


@router.get("/api/settings", response_model=Settings)
def get_settings(file_controller: "FilesController" = Depends(get_file_manager)):
    return file_controller.load_settings()


@router.post("/api/settings", response_model=Settings)
def update_settings(
    new_settings: Settings,
    file_controller: "FilesController" = Depends(get_file_manager),
):
    data = new_settings.model_dump(exclude_none=True, exclude_defaults=True)

    file_controller.save_settings(data)
    return new_settings


@router.get("/api/calibration", response_model=CalibrationConfig)
def get_calibration_settings(
    file_controller: "FilesController" = Depends(get_file_manager),
):
    return file_controller.get_calibration_config()


@router.get("/api/detectors", response_model=DetectorsResponse)
def get_detectors():
    return {"detectors": list(detectors.keys())}


@router.get("/api/enhancers", response_model=EnhancersResponse)
def get_frame_enhancers():
    return {"enhancers": list(frame_enhancers.keys())}


@router.get("/api/video-modes", response_model=VideoModesResponse)
def get_video_modes():
    return {
        "detectors": list(detectors.keys()),
        "enhancers": list(frame_enhancers.keys()),
    }
