from time import localtime, strftime
from typing import TYPE_CHECKING

import numpy as np
from app.deps import get_camera_manager, get_file_manager
from app.util.logger import Logger
from app.util.photo import capture_photo
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from app.controllers.camera_controller import CameraController
    from app.controllers.files_controller import FilesController

router = APIRouter()
logger = Logger(__name__)


@router.get("/api/take-photo")
async def take_photo(
    camera_manager: "CameraController" = Depends(get_camera_manager),
    file_manager: "FilesController" = Depends(get_file_manager),
):
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
        return JSONResponse(content={"file": name})
    raise HTTPException(status_code=400, detail="Couldn't take photo")


@router.get("/api/frame-dimensions")
async def frame_dimensions(
    camera_manager: "CameraController" = Depends(get_camera_manager),
):
    await camera_manager.start_camera_and_wait_for_stream_img()
    frame_array = np.array(camera_manager.stream_img, dtype=np.uint8)
    height, width = frame_array.shape[:2]
    return JSONResponse(content={"width": width, "height": height})
