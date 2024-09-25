from typing import TYPE_CHECKING

from app.deps import get_file_manager
from app.exceptions.file_controller import DefaultFileRemoveAttempt
from app.schemas.file_management import (
    FilesResponse,
    RemoveFileResponse,
    UploadFileResponse,
)
from app.util.logger import Logger
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from starlette.responses import FileResponse

if TYPE_CHECKING:
    from app.controllers.files_controller import FilesController

router = APIRouter()
logger = Logger(__name__)


@router.get("/api/list_files/{media_type}", response_model=FilesResponse)
def list_files(
    media_type: str, file_manager: "FilesController" = Depends(get_file_manager)
):
    if media_type == "music":
        files = file_manager.list_user_music()
        logger.debug(f"music files {files}")
    elif media_type == "default_music":
        files = file_manager.list_default_music()
    elif media_type == "default_sound":
        files = file_manager.list_default_sounds()
    elif media_type == "sound":
        files = file_manager.list_user_sounds()
    elif media_type == "image":
        files = file_manager.list_user_photos()
    else:
        raise HTTPException(status_code=400, detail="Invalid media type")

    return {"files": files}


@router.post("/api/upload/{media_type}", response_model=UploadFileResponse)
def upload_file(
    media_type: str,
    file: UploadFile = File(...),
    file_manager: "FilesController" = Depends(get_file_manager),
):
    if file.filename == "":
        raise HTTPException(status_code=400, detail="No selected file")

    if media_type == "music":
        file_manager.save_music(file)
    elif media_type == "sound":
        file_manager.save_sound(file)
    elif media_type == "image":
        file_manager.save_photo(file)
    else:
        raise HTTPException(status_code=400, detail="Invalid media type")

    return {"success": True, "filename": file.filename}


@router.delete(
    "/api/remove_file/{media_type}/{filename}", response_model=RemoveFileResponse
)
def remove_file(
    media_type: str,
    filename: str,
    file_manager: "FilesController" = Depends(get_file_manager),
):
    try:
        if media_type == "music":
            file_manager.remove_music(filename)
        elif media_type == "sound":
            file_manager.remove_sound(filename)
        elif media_type == "image":
            file_manager.remove_photo(filename)
        else:
            raise HTTPException(status_code=400, detail="Invalid media type")
        return {"success": True, "filename": filename}
    except DefaultFileRemoveAttempt as e:
        logger.warning(f"Duplicate notification attempted: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.get(
    "/api/download/{media_type}/{filename}",
    responses={
        200: {
            "content": {"application/octet-stream": {}},
            "description": "A file will be returned.",
        },
        400: {"description": "Invalid media type"},
        404: {"description": "File not found"},
    },
)
def download_file(
    media_type: str,
    filename: str,
    file_manager: "FilesController" = Depends(get_file_manager),
):
    try:
        if media_type == "music":
            directory = file_manager.get_music_directory(filename)
        elif media_type == "sound":
            directory = file_manager.get_sound_directory(filename)
        elif media_type == "image":
            directory = file_manager.get_photo_directory(filename)
        else:
            raise HTTPException(status_code=400, detail="Invalid media type")
        return FileResponse(
            path=f"{directory}/{filename}",
            media_type="application/octet-stream",
            filename=filename,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
