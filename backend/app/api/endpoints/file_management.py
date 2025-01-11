"""
Endpoints for managing files, including uploading, listing, downloading, and deleting files.
"""

import asyncio
import os
import zipfile
from io import BytesIO
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

from app.api.deps import get_file_manager, get_music_manager
from app.exceptions.file_exceptions import (
    DefaultFileRemoveAttempt,
    InvalidFileName,
    InvalidMediaType,
)
from app.exceptions.music import ActiveMusicTrackRemovalError, MusicPlayerError
from app.schemas.file_management import (
    BatchRemoveFilesRequest,
    DownloadArchiveRequestPayload,
    PhotosResponse,
    RemoveFileResponse,
    UploadFileResponse,
)
from app.util.file_util import resolve_absolute_path
from app.util.logger import Logger
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from starlette.responses import FileResponse

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.file_service import FileService
    from app.services.music_service import MusicService

router = APIRouter()
logger = Logger(__name__)

octet_stream_response = {
    "content": {
        "application/octet-stream": {
            "example": "This is a binary content, example isn't directly usable for file download."
        }
    },
}


@router.post(
    "/files/upload/{media_type}",
    response_model=UploadFileResponse,
    response_description="A response object with the filename and the status of uploading.",
    responses={
        400: {
            "description": "Bad Request. Invalid filename or media type.",
            "content": {
                "application/json": {"example": {"detail": "Invalid filename."}}
            },
        },
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {"example": {"detail": "Failed to upload the file"}}
            },
        },
    },
)
async def upload_file(
    request: Request,
    media_type: str,
    file: UploadFile = File(...),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Upload a file of a specific media type: 'music', 'image', 'video' or 'data'.

    Returns:
    --------------
    **UploadFileResponse**: A response object containing the success status and the filename.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    handlers: Dict[str, Callable[[UploadFile], str]] = {
        "music": file_manager.save_music,
        "image": file_manager.save_photo,
        "data": file_manager.save_data,
    }

    try:
        handler = handlers.get(media_type)
        if not handler:
            raise InvalidMediaType("Invalid media type.")
        result = await asyncio.to_thread(handler, file)
        if result:
            await connection_manager.broadcast_json(
                {
                    "type": "uploaded",
                    "payload": [{"file": file.filename, "type": media_type}],
                }
            )
        return {"success": True, "filename": file.filename}
    except InvalidFileName:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    except InvalidMediaType:
        logger.error(f"Invalid media type '{media_type}' for '{file.filename}'")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid media type {media_type}. Should be one of "
            + ", ".join(list(handlers.keys())),
        )
    except Exception:
        logger.error("Unhandled exception during file upload", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to upload the file.",
        )


@router.delete(
    "/files/remove/{media_type}/{filename}",
    response_model=RemoveFileResponse,
    response_description="A response object with the filename, "
    "the status of removal, and "
    "optionally an error message if the file wasn't removed successfully.",
    responses={
        400: {
            "description": "Bad Request. Invalid media type is given; "
            "default file or active music track is trying to be removed.",
            "content": {
                "application/json": {
                    "example": {"detail": "Cannot remove the default file."}
                }
            },
        },
        404: {
            "description": "Not Found. The file is not found or can't be resolved.",
            "content": {
                "application/json": {"example": {"detail": "File is not found."}}
            },
        },
        500: {
            "description": "Internal Server Error. Unexpected error occurred.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to remove 'my_file.wav'"}
                }
            },
        },
    },
)
async def remove_file(
    request: Request,
    media_type: str,
    filename: str,
    file_manager: "FileService" = Depends(get_file_manager),
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Remove a file of a specific media type: 'music', 'video', 'image' or 'data'.

    Returns:
    --------------
    - **RemoveFileResponse**: A response object containing the success status and the filename.
    """
    handlers: Dict[str, Callable[[str], bool]] = {
        "music": music_player.remove_music_track,
        "image": file_manager.remove_photo,
        "video": file_manager.remove_video,
        "data": file_manager.remove_data,
    }

    handler = handlers.get(media_type)
    connection_manager: "ConnectionService" = request.app.state.app_manager

    logger.info("Removing file '%s' of type '%s'", filename, media_type)
    try:
        if not handler:
            raise InvalidMediaType("Invalid media type.")
        result = await asyncio.to_thread(handler, filename)
        if result:
            await connection_manager.broadcast_json(
                {"type": "removed", "payload": [{"file": filename, "type": media_type}]}
            )
        return {"success": result, "filename": filename}
    except InvalidMediaType:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid media type {media_type}. Should be one of "
            + ", ".join(list(handlers.keys())),
        )

    except (ActiveMusicTrackRemovalError, DefaultFileRemoveAttempt) as e:
        logger.warning(str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        logger.warning(f"File %s is not found", filename)
        raise HTTPException(status_code=404, detail="File is not found")
    except Exception:
        logger.error(
            f"Unhandled error while removing file '{filename}' with media type '{media_type}'",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to remove '{filename}'")


@router.get(
    "/files/download/{media_type}/{filename}",
    response_description="The file response to download.",
    response_class=FileResponse,
    responses={
        200: {
            **octet_stream_response,
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
    Download a file of a specific media type: 'music', 'image', 'video' or 'data'.

    Returns:
    --------------
    - **FileResponse**: A response containing the file to download.
    """
    try:
        if media_type == 'data':
            path = resolve_absolute_path(filename, file_manager.data_dir)
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
            raise HTTPException(status_code=400, detail="Invalid Media Type")
        return FileResponse(
            path=f"{directory}/{filename}",
            media_type="application/octet-stream",
            filename=filename,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.post(
    "/files/download/archive",
    response_description="The archived file response to download multiple files.",
    response_class=StreamingResponse,
    responses={
        200: {
            **octet_stream_response,
            "description": "An archive will be returned containing the requested files.",
            "headers": {
                "Content-Disposition": {
                    "description": "Specifies that the response content is an attachment.",
                    "example": 'attachment; filename="music_files_archive.zip"',
                }
            },
        },
        404: {
            "description": "One or more files not found",
            "content": {
                "application/json": {
                    "example": {"detail": "File not found: my_unexisting_file"}
                }
            },
        },
        422: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "literal_error",
                                "loc": ["body", "media_type"],
                                "msg": "Input should be 'music', 'image', 'video' or 'data'",
                                "input": "images",
                                "ctx": {
                                    "expected": "'music', 'image', 'video' or 'data'"
                                },
                            }
                        ]
                    }
                }
            },
        },
        400: {
            "description": "Invalid file request",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid media type 'my_media_type'. Should be one of: "
                        "'music', 'image', 'video', 'data'. "
                    }
                }
            },
        },
    },
)
def download_files_as_archive(
    payload: DownloadArchiveRequestPayload,
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Download multiple files of a specific media type (e.g., 'music', 'image', 'video', or 'data') as an archive.

    Returns:
    --------------
    - A response delivering the ZIP archive containing the requested files.
    """
    directory_resolvers: Dict[str, Callable[[str], str]] = {
        "music": file_manager.get_music_directory,
        "image": file_manager.get_photo_directory,
        "video": file_manager.get_video_directory,
        "data": lambda _: file_manager.data_dir,
    }
    try:

        directory_fn = directory_resolvers.get(payload.media_type)

        if directory_fn is None:
            raise InvalidMediaType("Invalid media type.")

        zip_stream = BytesIO()
        with zipfile.ZipFile(zip_stream, mode="w") as zipf:
            for filename in payload.filenames:
                directory = directory_fn(filename)

                file_path = os.path.join(directory, filename)

                if not os.path.isfile(file_path):
                    raise HTTPException(
                        status_code=404, detail=f"File not found: {filename}"
                    )

                zipf.write(file_path, arcname=filename)

        zip_stream.seek(0)

        archive_name = f"{payload.media_type}_files_archive.zip"

        return StreamingResponse(
            zip_stream,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{archive_name}"'},
        )
    except InvalidMediaType:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid media type '{payload.media_type}'. Should be one of: "
            + ", ".join(list(directory_resolvers.keys())),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating archive: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/files/preview/{filename}",
    response_class=FileResponse,
    responses={
        200: {
            "content": {
                "image/jpeg": {
                    "example": "This is a binary content, "
                    "example isn't directly usable for file download."
                },
                "image/png": {
                    "example": "This is a binary content, "
                    "example isn't directly usable for file download."
                },
            },
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

    Returns:
    --------------
    **FileResponse**: A response containing the preview image.
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


@router.get(
    "/files/list/photos",
    response_model=PhotosResponse,
    response_description="List of the user photos. "
    "Each photo contains the name "
    "of the filename without directory, but with extension, "
    "full path, and preview URL.",
)
def list_photos(file_manager: "FileService" = Depends(get_file_manager)):
    """
    List the captured by user photos.
    """

    return {"files": file_manager.list_user_photos_with_preview()}


@router.get(
    "/files/download-last-video",
    response_description="A response containing the most recent video to download.",
    response_class=FileResponse,
    responses={
        200: {
            **octet_stream_response,
            "description": "A file will be returned.",
        },
        404: {"description": "File not found"},
    },
)
def fetch_last_video(file_manager: "FileService" = Depends(get_file_manager)):
    """
    Download the last video captured by the user.

    Returns:
    --------------
    - `FileResponse`: A response containing the most recent video to download.
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


@router.post(
    "/files/remove-batch/{media_type}",
    response_model=List[RemoveFileResponse],
    response_description="A list of objects with the filename, "
    "the status of removal, and "
    "optionally an error message if the file wasn't removed successfully.",
    responses={
        400: {
            "description": "Bad Request. Invalid media type is given.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid media type 'photo'. Should be one of: music, image, video, data."
                    }
                }
            },
        },
    },
)
async def batch_remove_files(
    request: Request,
    media_type: str,
    request_body: BatchRemoveFilesRequest,
    file_manager: "FileService" = Depends(get_file_manager),
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Batch remove multiple files of a specific media type: 'music', 'image', 'video', or 'data'.

    Returns:
    --------------
    A list of response objects for each file with success status and the filename.
    """
    filenames = request_body.filenames
    if len(filenames) <= 0:
        raise HTTPException(status_code=400, detail="No files to remove!")
    handlers: Dict[str, Callable[[str], bool]] = {
        "music": music_player.remove_music_track,
        "image": file_manager.remove_photo,
        "video": file_manager.remove_video,
        "data": file_manager.remove_data,
    }

    handler = handlers.get(media_type)
    connection_manager: "ConnectionService" = request.app.state.app_manager

    if not handler:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid media type {media_type}. Should be one of: "
            + ", ".join(list(handlers.keys())),
        )
    responses: List[RemoveFileResponse] = []
    success_responses = []
    for filename in filenames:
        logger.info("Removing file '%s' of type '%s'", filename, media_type)
        result = False
        error: Optional[str] = None
        try:
            result = await asyncio.to_thread(handler, filename)
        except (DefaultFileRemoveAttempt, MusicPlayerError) as e:
            error = str(e)
            logger.warning(error)
        except FileNotFoundError:
            error = "File not found"
            logger.warning("Failed to remove file %s: not found", filename)
        except Exception:
            error = "Internal server error"
            logger.error(
                f"Unhandled error while removing file '{filename}' with media type '{media_type}'",
                exc_info=True,
            )
        finally:
            responses.append(
                RemoveFileResponse(
                    **{"success": result, "filename": filename, "error": error}
                )
            )
            if result:
                success_responses.append({"file": filename, "type": media_type})

    if success_responses:
        await connection_manager.broadcast_json(
            {
                "type": "removed",
                "payload": success_responses,
            }
        )

    return responses
