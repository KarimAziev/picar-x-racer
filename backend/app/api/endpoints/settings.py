from typing import TYPE_CHECKING

from app.api.deps import get_camera_manager, get_detection_manager, get_file_manager
from app.config.video_enhancers import frame_enhancers
from app.config.yolo_common_models import get_available_models
from app.schemas.settings import (
    CalibrationConfig,
    CameraDevicesResponse,
    EnhancersResponse,
    Settings,
    UpdateCameraDevice,
    VideoModesResponse,
)
from app.util.device import list_available_camera_devices
from fastapi import APIRouter, Depends

if TYPE_CHECKING:
    from app.services.camera_service import CameraService
    from app.services.detection_service import DetectionService
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
    camera_manager: "CameraService" = Depends(get_camera_manager),
    detection_manager: "DetectionService" = Depends(get_detection_manager),
):
    """
    Update the application settings.

    Args:
    - new_settings (Settings): The new settings to apply.
    - file_service (FilesService): The file service for managing settings.
    - camera_manager (CameraService): The camera service for managing the camera settings.
    - detection_manager (DetectionService): The detection service for managing the detection settings.


    Returns:
        `Settings`: The updated settings of the application.
    """
    data = new_settings.model_dump(exclude_unset=True)

    file_service.save_settings(data)

    for key, value in data.items():
        if hasattr(camera_manager, key) and getattr(camera_manager, key) != value:
            setattr(camera_manager, key, value)
        elif (
            hasattr(detection_manager, key) and getattr(detection_manager, key) != value
        ):
            setattr(detection_manager, key, value)

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


@router.get("/api/detection-models")
def get_detectors():
    """
    Retrieve a list of available object detectors.
    """
    return get_available_models()


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
        "detectors": get_available_models(),
        "enhancers": list(frame_enhancers.keys()),
    }


@router.get("/api/camera-devices", response_model=CameraDevicesResponse)
def get_camera_devices():
    """
    Retrieve available camera devices.
    """
    devices = list_available_camera_devices()
    return {"devices": devices}


@router.post("/api/camera-device", response_model=UpdateCameraDevice)
def update_camera_device(
    data: UpdateCameraDevice,
    camera_manager: "CameraService" = Depends(get_camera_manager),
):
    """
    Retrieve available camera devices.
    """

    camera_manager.update_device(data.device)
    info = camera_manager.video_device_adapter.video_device
    (device, _) = info or (None, None)

    return {"device": device}
