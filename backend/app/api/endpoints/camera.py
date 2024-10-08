from time import localtime, strftime
from typing import TYPE_CHECKING

import numpy as np
from app.api.deps import get_camera_manager, get_file_manager
from app.schemas.camera import FrameDimensionsResponse, PhotoResponse
from app.util.logger import Logger
from app.util.photo import capture_photo
from fastapi import APIRouter, Depends, HTTPException

if TYPE_CHECKING:
    from app.services.camera_service import CameraService
    from app.services.files_service import FilesService

router = APIRouter()
logger = Logger(__name__)


@router.get("/api/take-photo", response_model=PhotoResponse, summary="Capture a photo")
async def take_photo(
    camera_manager: "CameraService" = Depends(get_camera_manager),
    file_manager: "FilesService" = Depends(get_file_manager),
):
    """
    Endpoint to capture a photo.

    Args:
    - *camera_manager (CameraService)*: The camera service for managing the camera operations
    - *file_manager (FilesService)*: The file service for managing file paths

    Returns:
        `PhotoResponse`: A response object containing the filename of the captured photo.

    Raises:
        HTTPException (400): If the photo could not be taken.
    """
    _time = strftime("%Y-%m-%d-%H-%M-%S", localtime())
    name = f"photo_{_time}.jpg"

    await camera_manager.start_camera_and_wait_for_stream_img()

    status = (
        await capture_photo(
            img=camera_manager.img, photo_name=name, path=file_manager.user_photos_dir
        )
        if camera_manager.img is not None
        else False
    )
    if status:
        return {"file": name}
    raise HTTPException(status_code=400, detail="Couldn't take photo")


@router.get(
    "/api/frame-dimensions", response_model=FrameDimensionsResponse, tags=["camera"]
)
async def frame_dimensions(
    camera_manager: "CameraService" = Depends(get_camera_manager),
):
    """
    Endpoint to get the dimensions of the current camera frame.

    Args:
    - `camera_manager` (CameraService): The camera service for managing the camera operations.

    Returns:
        `FrameDimensionsResponse`: A response object containing the width and height of the current camera frame.
    """
    await camera_manager.start_camera_and_wait_for_stream_img()
    frame_array = np.array(camera_manager.stream_img, dtype=np.uint8)
    height, width = frame_array.shape[:2]
    return {"width": width, "height": height}
