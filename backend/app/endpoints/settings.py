from typing import TYPE_CHECKING, Any, Dict, Union

from app.config.detectors import detectors
from app.config.video_enhancers import frame_enhancers
from app.deps import get_file_manager
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from app.controllers.files_controller import FilesController


router = APIRouter()


@router.get("/api/settings")
def get_settings(file_controller: "FilesController" = Depends(get_file_manager)):
    return JSONResponse(content=file_controller.load_settings())


@router.post("/api/settings")
async def update_settings(
    new_settings: Union[Dict[str, Any], None],
    file_controller: "FilesController" = Depends(get_file_manager),
):
    if not isinstance(new_settings, dict):
        raise HTTPException(status_code=400, detail="Invalid settings format")

    file_controller.save_settings(new_settings)
    return JSONResponse(content={"success": True, "settings": new_settings})


@router.get("/api/calibration")
async def get_calibration_settings(
    file_controller: "FilesController" = Depends(get_file_manager),
):
    return JSONResponse(content=file_controller.get_calibration_config())


@router.get("/api/detectors")
async def get_detectors():
    return JSONResponse(content={"detectors": list(detectors.keys())})


@router.get("/api/enhancers")
async def get_frame_enhancers():
    return JSONResponse(content={"enhancers": list(frame_enhancers.keys())})


@router.get("/api/video-modes")
async def get_video_modes():
    return JSONResponse(
        content={
            "detectors": list(detectors.keys()),
            "enhancers": list(frame_enhancers.keys()),
        }
    )
