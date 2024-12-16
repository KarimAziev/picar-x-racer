import asyncio
from typing import TYPE_CHECKING

from app.api.deps import get_file_manager, get_music_manager
from app.config.paths import DATA_DIR
from app.exceptions.file_exceptions import DefaultFileRemoveAttempt
from app.schemas.file_management import (
    PhotosResponse,
    RemoveFileResponse,
    UploadFileResponse,
)
from app.util.file_util import resolve_absolute_path
from app.util.logger import Logger
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from starlette.responses import FileResponse

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.file_service import FileService
    from app.services.music_service import MusicService

router = APIRouter()
logger = Logger(__name__)


@router.post("/api/files/upload/{media_type}", response_model=UploadFileResponse)
async def upload_file(
    request: Request,
    media_type: str,
    file: UploadFile = File(...),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Upload a file of a specific media type.

    Args:
    --------------
    - media_type (str): The type of media to upload ('music', 'image', 'data' etc).
    - file (UploadFile): The file to upload.
    - file_manager (FileService): The file management service.

    Returns:
    --------------
    `UploadFileResponse`: A response object containing the success status and the filename.

    Raises:
    --------------
    `HTTPException`: If no file is selected or the media type is invalid.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    if file.filename == "":
        raise HTTPException(status_code=400, detail="No selected file")

    handlers = {
        "music": file_manager.save_music,
        "image": file_manager.save_photo,
        "data": file_manager.save_data,
    }
    handler = handlers.get(media_type)

    if not handler:
        raise HTTPException(status_code=400, detail="Invalid media type")

    result = await asyncio.to_thread(handler, file)
    if result:
        await connection_manager.broadcast_json(
            {"type": "uploaded", "payload": {"file": file.filename, "type": media_type}}
        )
    return {"success": True, "filename": file.filename}


@router.delete(
    "/api/files/remove/{media_type}/{filename}", response_model=RemoveFileResponse
)
async def remove_file(
    request: Request,
    media_type: str,
    filename: str,
    file_manager: "FileService" = Depends(get_file_manager),
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Remove a file of a specific media type.

    Args:
    --------------
    - media_type (str): The type of media ('music', 'video', 'image', 'data').
    - filename (str): The name of the file to remove.
    - file_manager (FileService): The file management service.

    Returns:
    --------------
    - `RemoveFileResponse`: A response object containing the success status and the filename.

    Raises:
    --------------
    - `HTTPException`: If the media type is invalid, or the file could not be removed or found.
    """
    handlers = {
        "music": music_player.remove_music_track,
        "image": file_manager.remove_photo,
        "video": file_manager.remove_video,
        "data": file_manager.remove_data,
    }

    handler = handlers.get(media_type)
    connection_manager: "ConnectionService" = request.app.state.app_manager

    logger.info("Removing file %s of type %s", filename, media_type)

    if not handler:
        raise HTTPException(status_code=400, detail="Invalid media type")

    try:
        result = await asyncio.to_thread(handler, filename)
        if result:
            await connection_manager.broadcast_json(
                {"type": "removed", "payload": {"file": filename, "type": media_type}}
            )
        return {"success": result, "filename": filename}
    except DefaultFileRemoveAttempt as e:
        logger.warning(str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception:
        logger.error(f"Error removing file {filename}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get(
    "/api/files/download/{media_type}/{filename}",
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
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Download a file of a specific media type.

    Args:
    --------------
    - media_type (str): The type of media ('music', 'image', 'video', 'data').
    - filename (str): The name of the file to download.
    - file_manager (FileService): The file management service.

    Returns:
    --------------
    - `FileResponse`: A response containing the file to download.

    Raises:
    --------------
    - `HTTPException`: If the media type is invalid or the file is not found.
    """
    try:
        if media_type == 'data':
            path = resolve_absolute_path(filename, DATA_DIR)
            return FileResponse(
                path=path,
                media_type="application/octet-stream",
                filename=filename,
            )
        if media_type == "music":
            directory = file_manager.get_music_directory(filename)
        elif media_type == "image":
            directory = file_manager.get_photo_directory(filename)
        elif media_type == "video":
            directory = file_manager.get_video_directory(filename)
        else:
            raise HTTPException(status_code=400, detail="Invalid media type")
        return FileResponse(
            path=f"{directory}/{filename}",
            media_type="application/octet-stream",
            filename=filename,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.get(
    "/api/files/preview/{filename}",
    responses={
        200: {
            "content": {"image/jpeg": {}, "image/png": {}},
            "description": "A preview image will be returned.",
        },
        404: {"description": "File not found"},
    },
)
def preview_image(
    filename: str,
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Provide a preview image of a specific file.

    Args:
    --------------
    - filename (str): The name of the image file to preview.
    - file_manager (FileService): The file management service.

    Returns:
    --------------
    - `FileResponse`: A response containing the preview image.

    Raises:
    --------------
    - `HTTPException`: If the file is not found.
    """
    try:
        directory = file_manager.get_photo_directory(filename)
        full_path = f"{directory}/{filename}"
        return FileResponse(
            path=full_path,
            media_type=(
                "image/jpeg"
                if filename.lower().endswith(".jpg")
                or filename.lower().endswith(".jpeg")
                else "image/png"
            ),
            filename=filename,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.get("/api/files/list/photos", response_model=PhotosResponse)
def list_photos(file_manager: "FileService" = Depends(get_file_manager)):
    """
    List the captured by user photos.
    """

    return {"files": file_manager.list_user_photos_with_preview()}


@router.get(
    "/api/files/download-last-video",
    responses={
        200: {
            "content": {"application/octet-stream": {}},
            "description": "A file will be returned.",
        },
        404: {"description": "File not found"},
    },
)
def fetch_last_video(file_manager: "FileService" = Depends(get_file_manager)):
    """
    Download the last video captured by the user.

    Args:
    --------------
    - file_manager (FileService): The file management service for videos.

    Returns:
    --------------
    - `FileResponse`: A response containing the most recent video to download.

    Raises:
    --------------
    - `HTTPException`: If no videos are found.
    """
    videos = file_manager.list_user_videos()

    if not videos:
        raise HTTPException(status_code=404, detail="No videos found")

    filename = videos[0]
    directory = file_manager.get_video_directory(filename)

    return FileResponse(
        path=f"{directory}/{filename}",
        media_type="application/octet-stream",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
