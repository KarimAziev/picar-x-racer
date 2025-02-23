"""
Endpoints for managing files, including uploading, listing, downloading, and deleting files.
"""

import asyncio
import os
from typing import TYPE_CHECKING, Annotated, Callable, Dict, Generator, List, Optional

from app.api.deps import get_file_manager, get_music_service
from app.core.logger import Logger
from app.exceptions.file_exceptions import (
    DefaultFileRemoveAttempt,
    InvalidFileName,
    InvalidMediaType,
)
from app.exceptions.music import ActiveMusicTrackRemovalError, MusicPlayerError
from app.schemas.file_management import (
    BatchRemoveFilesRequest,
    DownloadArchiveRequestPayload,
    MediaType,
    PhotosResponse,
    RemoveFileResponse,
    UploadFileResponse,
    VideoDetail,
)
from app.util.file_util import resolve_absolute_path, zip_files_generator
from fastapi import (
    APIRouter,
    Depends,
    File,
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
    media_type: MediaType,
    file: UploadFile = File(...),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Upload a file of a specific media type: 'music', 'image', 'video' or 'data'.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    handlers: Dict[MediaType, Callable[[UploadFile], str]] = {
        MediaType.music: file_manager.save_music,
        MediaType.image: file_manager.save_photo,
        MediaType.data: file_manager.save_data,
        MediaType.video: file_manager.save_video,
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
    "/files/remove/{media_type}",
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
    media_type: Annotated[MediaType, Path(description="The type of the file.")],
    filename: str = Query(..., description="The name of the file"),
    file_manager: "FileService" = Depends(get_file_manager),
    music_player: "MusicService" = Depends(get_music_service),
):
    """
    Remove a file of a specific media type.

    Returns:
    --------------
    - **RemoveFileResponse**: A response object containing the success status and the filename.
    """
    handlers: Dict[MediaType, Callable[[str], bool]] = {
        MediaType.music: music_player.remove_music_track,
        MediaType.image: file_manager.remove_photo,
        MediaType.video: file_manager.remove_video,
        MediaType.data: file_manager.remove_data,
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
    "/files/download/{media_type}",
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
    media_type: Annotated[MediaType, Path(description="The type of the file")],
    filename: str = Query(..., description="The name of the file"),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Download a file of a specific media type: 'music', 'image', 'video' or 'data'.

    Returns:
    --------------
    - **FileResponse**: A response containing the file to download.
    """
    try:

        if media_type == MediaType.data:
            path = resolve_absolute_path(filename, file_manager.data_dir)
            return FileResponse(
                path=path,
                media_type="application/octet-stream",
                filename=filename,
            )
        if media_type == MediaType.music:
            directory = file_manager.get_music_directory(filename)
        elif media_type == MediaType.image:
            directory = file_manager.get_photo_directory(filename)
        elif media_type == MediaType.video:
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
    response_description="A successful response delivering the ZIP archive containing the requested files.",
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
    Download multiple files of a specific media type as an archive.
    """
    directory_resolvers: Dict[MediaType, Callable[[str], str]] = {
        MediaType.music: file_manager.get_music_directory,
        MediaType.image: file_manager.get_photo_directory,
        MediaType.video: file_manager.get_video_directory,
        MediaType.data: lambda _: file_manager.data_dir,
    }

    try:

        directory_fn = directory_resolvers.get(payload.media_type)

        if directory_fn is None:
            raise InvalidMediaType("Invalid media type.")

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
    "/files/image/preview",
    response_class=FileResponse,
    response_description="A response containing the preview image.",
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
    filename: str = Query(..., description="The name of the file"),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Provide a preview image of a specific file.
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
            filename=os.path.basename(filename),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.get(
    "/files/video/preview",
    response_class=FileResponse,
    response_description="A response containing the preview image.",
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
def preview_video(
    filename: str = Query(..., description="The name of the file"),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Provide a preview image of a specific video file.
    """
    try:
        full_path = file_manager.preview_video_image(filename)
        logger.info("full_path=%s, filename='%s'", full_path, filename)

        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail=f"File {filename} not found")
        return FileResponse(
            path=full_path,
            media_type=(
                "image/jpeg"
                if filename.lower().endswith(".jpg")
                or filename.lower().endswith(".jpeg")
                else "image/png"
            ),
            filename=os.path.basename(full_path),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.get(
    "/files/list/videos",
    response_model=List[VideoDetail],
    response_description="List of the a video filename's metadata."
    "Each filename contains the name "
    "of the video filename relative to video directory, preview filename and duration.",
)
def list_videos(file_manager: "FileService" = Depends(get_file_manager)):
    """
    List the captured by user videos.
    """

    return file_manager.list_user_videos_detailed()


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
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
            "Expires": "0",
        },
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
    media_type: Annotated[MediaType, Path(description="The type of the file")],
    request_body: BatchRemoveFilesRequest,
    file_manager: "FileService" = Depends(get_file_manager),
    music_player: "MusicService" = Depends(get_music_service),
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
        MediaType.music: music_player.remove_music_track,
        MediaType.image: file_manager.remove_photo,
        MediaType.video: file_manager.remove_video,
        MediaType.data: file_manager.remove_data,
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


@router.get(
    "/files/stream/video",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "video/mp4": {"example": "This is a streamed video response."},
                "video/x-msvideo": {"example": "This is a streamed video response."},
                "video/quicktime": {"example": "This is a streamed video response."},
                "video/x-matroska": {"example": "This is a streamed video response."},
            },
            "description": "A video file will be streamed.",
        },
        206: {
            "content": {
                "video/mp4": {
                    "example": "This is a streamed video response supporting partial content."
                },
                "video/x-msvideo": {
                    "example": "This is a streamed video response with byte-ranges."
                },
            },
            "description": "Partial content streaming for video.",
        },
        404: {"description": "File not found"},
        416: {"description": "Invalid byte range"},
    },
)
def stream_video(
    filename: str = Query(..., min_length=1, description="The name of the video file"),
    range_header: Optional[str] = Header(None),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """Supports partial content video streaming with FastAPI."""

    try:
        directory = file_manager.get_video_directory(filename)

        file_path = os.path.join(directory, filename)
        file_path = file_manager.video_service.convert_to_mp4(file_path)
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

    content_type = media_types.get(file_extension, "video/mp4")
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
            status_code=206,  # Partial Content
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
