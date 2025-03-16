"""
Endpoints for managing files, including uploading, listing, downloading, and deleting files.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
from typing import TYPE_CHECKING, Annotated, Callable, Dict, Generator, List, Optional

from app.api.deps import get_file_manager, get_music_service
from app.core.logger import Logger
from app.exceptions.file_exceptions import (
    DefaultFileRemoveAttempt,
    InvalidFileName,
    InvalidMediaType,
)
from app.exceptions.music import ActiveMusicTrackRemovalError
from app.schemas.file_filter import FileFilterRequest, FileResponseModel, OrderingModel
from app.schemas.file_management import (
    BatchFileResult,
    BatchFilesMoveRequest,
    BatchRemoveFilesRequest,
    DownloadArchiveRequestPayload,
    MakeDirRequest,
    MakeDirResponse,
    MediaType,
    RenameFileRequest,
    RenameFileResponse,
    SaveFileRequest,
    UploadFileResponse,
)
from app.util.atomic_write import atomic_write
from app.util.file_util import (
    guess_mime_type,
    resolve_absolute_path,
    zip_files_generator,
)
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from starlette.responses import FileResponse

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.file_manager_service import FileManagerService
    from app.services.file_service import FileService
    from app.services.music_service import MusicService

router = APIRouter()
logger = Logger(__name__)

octet_stream_response = {
    "content": {
        "application/octet-stream": {
            "example": "This is binary content; the example is not directly usable for file downloads."
        }
    },
}


@router.post(
    "/files/upload/{media_type}",
    response_model=UploadFileResponse,
    response_description="A response describing the result of the file upload.",
    responses={
        400: {
            "description": "Bad Request. Invalid filename or media type.",
            "content": {
                "application/json": {"example": {"detail": "Invalid filename."}}
            },
        },
        500: {
            "description": "Internal Server Error. An unexpected error occurred.",
            "content": {
                "application/json": {"example": {"detail": "Failed to upload the file"}}
            },
        },
    },
)
async def upload_file(
    request: Request,
    media_type: MediaType,
    file: UploadFile = File(...),
    dir: Optional[str] = Form(None),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Upload a file for the specified media type ('music', 'image', 'video', or 'data').
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    manager = file_manager.get_handler_by_dir_alias(media_type)
    try:
        result = await asyncio.to_thread(manager.save_uploaded_file, file, dir)
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
    except Exception:
        logger.error("Unhandled exception during file upload", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload the file.")


@router.delete(
    "/files/remove/{media_type}",
    response_model=BatchFileResult,
    response_description="A response indicating the result of the removal operation.",
    responses={
        400: {
            "description": "Bad Request. Invalid media type; removal of a default file or an active music track is not allowed.",
            "content": {
                "application/json": {
                    "example": {"detail": "Cannot remove the default file."}
                }
            },
        },
        404: {
            "description": "Not Found. The file could not be found or resolved.",
            "content": {"application/json": {"example": {"detail": "File not found."}}},
        },
        500: {
            "description": "Internal Server Error. An unexpected error occurred.",
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
    media_type: Annotated[MediaType, Path(description="The type of the file.")],
    filename: str = Query(
        ..., description="The file's name (relative to its media type directory)"
    ),
    file_manager: "FileService" = Depends(get_file_manager),
    music_player: "MusicService" = Depends(get_music_service),
):
    """
    Remove a file for the specified media type.
    """
    manager = file_manager.get_handler_by_dir_alias(media_type)
    handlers: Dict[MediaType, Callable[[str], bool]] = {
        MediaType.music: music_player.remove_music_track,
        MediaType.image: manager.remove_file,
        MediaType.video: manager.remove_file,
        MediaType.data: manager.remove_file,
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
            detail=f"Invalid media type {media_type}. Should be one of: "
            + ", ".join(map(str, handlers.keys())),
        )
    except (ActiveMusicTrackRemovalError, DefaultFileRemoveAttempt) as e:
        logger.warning(str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        logger.warning("File %s not found", filename)
        raise HTTPException(status_code=404, detail="File not found")
    except Exception:
        logger.error(
            "Unhandled error while removing file '%s' with media type '%s'",
            filename,
            media_type,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to remove '{filename}'")


@router.get(
    "/files/download/{media_type}",
    response_description="A file for download.",
    response_class=FileResponse,
    responses={
        200: {
            **octet_stream_response,
            "description": "A file is returned.",
        },
        400: {"description": "Invalid media type."},
        404: {"description": "File not found."},
    },
)
def download_file(
    media_type: Annotated[MediaType, Path(description="The type of the file")],
    filename: str = Query(
        ..., description="The file's name (relative to its media type directory)"
    ),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Download a file for the specified media type.
    """
    try:
        manager = file_manager.get_handler_by_dir_alias(media_type)
        directory = manager.root_directory
        full_path = resolve_absolute_path(filename, directory)
        if not os.path.isdir(full_path):
            guessed_mime_type = guess_mime_type(full_path)
            return FileResponse(
                path=f"{directory}/{filename}",
                media_type=guessed_mime_type or "application/octet-stream",
                filename=filename,
            )
        else:
            try:
                directory_fn = lambda _: manager.root_directory
                archive_name = f"{filename}.zip"
                logger.info(f"Created archive {archive_name}")
                buffer, content_length = zip_files_generator(
                    filenames=[filename], directory_fn=directory_fn
                )
                return StreamingResponse(
                    iter(lambda: buffer.read(4096), b""),
                    media_type="application/zip",
                    headers={
                        "Content-Disposition": f'attachment; filename="{archive_name}"',
                        "Cache-Control": "no-store",
                        "Pragma": "no-cache",
                        "Expires": "0",
                        "Content-Length": str(content_length),
                    },
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error creating archive: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.post(
    "/files/download/archive",
    response_description="A ZIP archive containing the requested files is delivered.",
    response_class=StreamingResponse,
    responses={
        200: {
            **octet_stream_response,
            "description": "An archive containing the requested files is returned.",
            "headers": {
                "Content-Disposition": {
                    "description": "Specifies that the response content is an attachment.",
                    "example": 'attachment; filename="music_files_archive.zip"',
                }
            },
        },
        404: {
            "description": "One or more files were not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "File not found: my_nonexistent_file"}
                }
            },
        },
        422: {
            "description": "Validation error.",
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
            "description": "Invalid file request.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid media type 'my_media_type'. Should be one of: 'music', 'image', 'video', 'data'."
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
    Download multiple files as a ZIP archive for the specified media type.
    """
    manager = file_manager.get_handler_by_dir_alias(payload.media_type)
    try:
        directory_fn = lambda _: manager.root_directory
        archive_name = payload.archive_name
        logger.info(f"Created archive {archive_name}")
        buffer, content_length = zip_files_generator(payload.filenames, directory_fn)
        return StreamingResponse(
            iter(lambda: buffer.read(4096), b""),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{archive_name}"',
                "Cache-Control": "no-store",
                "Pragma": "no-cache",
                "Expires": "0",
                "Content-Length": str(content_length),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating archive: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/files/preview-image/{media_type}",
    response_class=FileResponse,
    response_description="A preview image is returned.",
    responses={
        200: {
            "content": {
                "image/jpeg": {
                    "example": "Binary JPEG content; the example is not directly usable."
                },
                "image/png": {
                    "example": "Binary PNG content; the example is not directly usable."
                },
            },
            "description": "A preview image is returned.",
        },
        404: {"description": "File not found."},
    },
)
def preview_image(
    media_type: Annotated[MediaType, Path(description="The type of the file.")],
    filename: str = Query(
        ..., description="The file's name (relative to its media type directory)"
    ),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Return a preview image for the specified file.
    """
    file_managers: Dict[MediaType, FileManagerService] = {
        MediaType.music: file_manager.music_file_manager,
        MediaType.image: file_manager.photo_file_manager,
        MediaType.video: file_manager.video_file_manager,
        MediaType.data: file_manager.data_file_manager,
    }
    manager = file_managers[media_type]
    try:
        directory = manager.root_directory
        full_path = f"{directory}/{filename}"
        return FileResponse(
            path=full_path,
            media_type=(
                "image/jpeg"
                if filename.lower().endswith((".jpg", ".jpeg"))
                else "image/png"
            ),
            filename=os.path.basename(filename),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.get(
    "/files/preview-video/{media_type}",
    response_class=FileResponse,
    response_description="A preview image for the video file is returned.",
    responses={
        200: {
            "content": {
                "image/jpeg": {
                    "example": "Binary JPEG content; the example is not directly usable."
                },
                "image/png": {
                    "example": "Binary PNG content; the example is not directly usable."
                },
            },
            "description": "A preview image is returned.",
        },
        404: {"description": "File not found."},
    },
)
def preview_video(
    media_type: Annotated[MediaType, Path(description="The type of the file.")],
    filename: str = Query(
        ..., description="The file's name (relative to its media type directory)"
    ),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Return a preview image for the specified video file.
    """
    try:
        manager = file_manager.get_handler_by_dir_alias(media_type)
        full_path = manager.video_preview(filename)
        if not full_path or not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail=f"File {filename} not found")
        return FileResponse(
            path=full_path,
            media_type=(
                "image/jpeg"
                if filename.lower().endswith((".jpg", ".jpeg"))
                else "image/png"
            ),
            filename=os.path.basename(full_path),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.post(
    "/files/list/{media_type}",
    response_model=FileResponseModel,
    response_description="A listing of files in the specified media type directory.",
)
def list_files(
    media_type: Annotated[MediaType, Path(description="The type of the file.")],
    request_data: FileFilterRequest,
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Return a list of files for the specified media type.
    """
    manager = file_manager.get_handler_by_dir_alias(media_type)
    result = manager.get_files(
        filter_model=request_data.filters,
        search=request_data.search,
        ordering=request_data.ordering,
        subdir=request_data.dir,
    )
    return result


@router.get(
    "/files/download-last-video",
    response_description="A response containing the most recent video for download.",
    response_class=FileResponse,
    responses={
        200: {
            **octet_stream_response,
            "description": "A video file is returned.",
        },
        404: {"description": "File not found."},
    },
)
def fetch_last_video(file_manager: "FileService" = Depends(get_file_manager)):
    """
    Return the most recent video file.
    """
    result = file_manager.video_file_manager.get_files(ordering=OrderingModel())
    video_file: Optional[str] = None
    for file in result.data:
        if file_manager.video_file_manager.is_video(file):
            video_file = os.path.join(
                file_manager.video_file_manager.root_directory, file.path
            )
            break
    if video_file is None:
        raise HTTPException(status_code=404, detail="No videos found")
    filename = os.path.basename(video_file)
    return FileResponse(
        path=video_file,
        media_type="application/octet-stream",
        filename=filename,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.post(
    "/files/remove-batch/{media_type}",
    response_model=List[BatchFileResult],
    response_description="A list of responses indicating the result for each file's removal.",
    responses={
        400: {
            "description": "Bad Request. Invalid media type.",
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
    media_type: Annotated[MediaType, Path(description="The type of the file")],
    request_body: BatchRemoveFilesRequest,
    file_manager: "FileService" = Depends(get_file_manager),
    music_player: "MusicService" = Depends(get_music_service),
):
    """
    Remove multiple files for the specified media type.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    filenames = request_body.filenames
    if len(filenames) <= 0:
        raise HTTPException(status_code=400, detail="No files to remove!")
    excluded_files: List[BatchFileResult] = []
    custom_order: Optional[List[str]] = None
    manager = file_manager.get_handler_by_dir_alias(media_type)
    if media_type == MediaType.music:
        custom_order = file_manager.get_custom_music_order()
        curr_state = music_player.current_state
        curr_track = curr_state["track"]
        if any(file == curr_track for file in filenames):
            music_player.next_track()
            if music_player.track == curr_track:
                filenames = [file for file in filenames if file != curr_track]
                excluded_files.append(
                    BatchFileResult(
                        success=False,
                        filename=curr_track,
                        error="The last music track cannot be removed",
                    )
                )
    if not manager:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid media type {media_type}. Should be one of: "
            + ", ".join(map(str, manager.keys())),
        )
    responses, success_responses = await asyncio.to_thread(
        manager.batch_remove_files, filenames
    )
    success_responses: List[Dict[str, str]] = [
        {**item, "type": media_type} for item in success_responses
    ]
    if custom_order:
        for item in success_responses:
            file = item.get("file")
            if file:
                custom_order.remove(file)
        await asyncio.to_thread(file_manager.save_custom_music_order, custom_order)
    if success_responses:
        await connection_manager.broadcast_json(
            {"type": "removed", "payload": success_responses}
        )
    return responses + excluded_files


@router.get(
    "/files/stream/{media_type}",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "video/mp4": {"example": "This is a streamed video response."},
                "video/x-msvideo": {"example": "This is a streamed video response."},
                "video/quicktime": {"example": "This is a streamed video response."},
                "video/x-matroska": {"example": "This is a streamed video response."},
            },
            "description": "A video file is streamed.",
        },
        206: {
            "content": {
                "video/mp4": {
                    "example": "This is a streamed video response supporting partial content."
                },
                "video/x-msvideo": {
                    "example": "This is a streamed video response with byte ranges."
                },
            },
            "description": "Partial content streaming for video.",
        },
        404: {"description": "File not found."},
        416: {"description": "Invalid byte range."},
    },
)
def stream_video(
    media_type: Annotated[MediaType, Path(description="The type of the file")],
    filename: str = Query(..., min_length=1, description="The name of the video file"),
    range_header: Optional[str] = Header(None),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Stream a video file with support for partial content.
    """
    logger.info("Streaming video %s, media_type=%s", filename, media_type)
    try:
        manager = file_manager.get_handler_by_dir_alias(media_type)
        file_path = manager.video_stream(filename)
        if file_path is None:
            raise HTTPException(status_code=503, detail="Failed to stream file")
        file_size = os.path.getsize(file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    media_types = {
        "mp4": "video/mp4",
        "avi": "video/x-msvideo",
        "mov": "video/quicktime",
        "mkv": "video/x-matroska",
    }
    file_extension = filename.split(".")[-1].lower()
    guessed_mime_type = guess_mime_type(file_path)
    content_type = guessed_mime_type or media_types.get(file_extension, "video/mp4")
    logger.info(f"file_extension='{file_extension}', content_type='{content_type}'")
    CHUNK_SIZE = 1024 * 1024  # 1MB chunks

    def file_generator(start: int, end: int) -> Generator[bytes, None, None]:
        with open(file_path, "rb") as file:
            file.seek(start)
            while start < end:
                data = file.read(min(CHUNK_SIZE, end - start))
                if not data:
                    break
                yield data
                start += len(data)

    if range_header:
        try:
            range_start, range_end = range_header.replace("bytes=", "").split("-")
            range_start = int(range_start) if range_start else 0
            range_end = int(range_end) if range_end else file_size - 1
        except ValueError:
            raise HTTPException(status_code=416, detail="Invalid byte range")
        if range_start >= file_size or range_end >= file_size:
            raise HTTPException(status_code=416, detail="Invalid byte range")
        content_length = range_end - range_start + 1
        headers = {
            "Content-Range": f"bytes {range_start}-{range_end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": content_type,
        }
        return StreamingResponse(
            file_generator(range_start, range_end + 1),
            status_code=206,
            headers=headers,
            media_type=content_type,
        )
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": content_type,
    }
    return StreamingResponse(
        file_generator(0, file_size), headers=headers, media_type=content_type
    )


@router.post(
    "/files/mkdir/{media_type}",
    response_model=MakeDirResponse,
    responses={
        400: {
            "description": "Bad Request. Invalid media type.",
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
async def mkdir(
    request: Request,
    media_type: Annotated[MediaType, Path(description="The type of the file")],
    request_body: MakeDirRequest,
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Create a new directory in the specified media type.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    filename = request_body.filename
    manager = file_manager.get_handler_by_dir_alias(media_type)
    logger.info("Creating directory %s", filename)
    file_path = pathlib.Path(os.path.join(manager.root_directory, filename))
    await asyncio.to_thread(file_path.mkdir, parents=True)
    await connection_manager.broadcast_json(
        {"type": "created", "payload": [{"type": media_type, "file": filename}]}
    )
    return {"success": file_path.exists(), "filename": filename}


@router.post(
    "/files/rename/{media_type}",
    response_model=RenameFileResponse,
    responses={
        400: {
            "description": "Bad Request. Invalid media type.",
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
async def mv(
    request: Request,
    media_type: Annotated[MediaType, Path(description="The type of the file")],
    request_body: RenameFileRequest,
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Rename a file or directory for the specified media type.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    filename = request_body.filename
    new_name = request_body.new_name
    manager = file_manager.get_handler_by_dir_alias(media_type)
    old_file_path = pathlib.Path(os.path.join(manager.root_directory, filename))
    file_path = pathlib.Path(os.path.join(manager.root_directory, new_name))
    await asyncio.to_thread(file_path.parent.mkdir, exist_ok=True, parents=True)
    await asyncio.to_thread(old_file_path.rename, file_path)
    await connection_manager.broadcast_json(
        {"type": "renamed", "payload": [{"type": media_type, "file": filename}]}
    )
    return {
        "success": file_path.exists() and not old_file_path.exists(),
        "error": None,
        "filename": filename,
        "new_name": new_name,
    }


@router.post(
    "/files/move/{media_type}",
    response_model=List[BatchFileResult],
    responses={
        400: {
            "description": "Bad Request. Invalid media type.",
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
async def move_files(
    request: Request,
    media_type: Annotated[MediaType, Path(description="The type of the file")],
    request_body: BatchFilesMoveRequest,
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Move multiple files or directories within the specified media type.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    manager = file_manager.get_handler_by_dir_alias(media_type)
    responses, success_responses = await asyncio.to_thread(
        manager.batch_move_files, request_body.filenames, request_body.dir
    )
    success_responses: List[Dict[str, str]] = [
        {**item, "type": media_type} for item in success_responses
    ]
    if success_responses:
        await connection_manager.broadcast_json(
            {"type": "moved", "payload": success_responses}
        )
    return responses


@router.put(
    "/files/save/{media_type}",
    response_model=SaveFileRequest,
    responses={
        400: {"description": "Bad Request: Error writing file."},
        500: {"description": "Internal Server Error: Error writing file."},
    },
)
async def save_file(
    media_type: Annotated[MediaType, Path(description="The type of the file")],
    payload: SaveFileRequest,
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Save or update the content of a file.
    """
    try:
        manager = file_manager.get_handler_by_dir_alias(media_type)
        dir = (
            resolve_absolute_path(payload.dir, manager.root_directory)
            if payload.dir
            else manager.root_directory
        )

        full_path = resolve_absolute_path(payload.path, dir)
        logger.info(
            "Writing the file %s, resolved dir %s, payload.dir %s",
            full_path,
            dir,
            payload.dir,
        )
        with atomic_write(full_path, mode="w") as f:
            f.write(payload.content)
        return payload
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Error writing file: {ex}")
