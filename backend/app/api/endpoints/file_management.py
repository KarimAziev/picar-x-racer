"""
Endpoints for managing files, including uploading, listing, downloading, and deleting files.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
from typing import TYPE_CHECKING, Annotated, Dict, List, Optional

from app.api import deps
from app.api.responses.file_management import (
    alias_dir_validation_error_response,
    audio_stream_responses,
    download_archive_responses,
    download_file_responses,
    download_video_responses,
    image_preview_responses,
    remove_file_responses,
    upload_responses,
    video_stream_responses,
    write_file_responses,
)
from app.core.logger import Logger
from app.exceptions.file_exceptions import DefaultFileRemoveAttempt, InvalidFileName
from app.exceptions.music import ActiveMusicTrackRemovalError
from app.managers.file_management.file_manager import FileManager
from app.schemas.file_filter import (
    FileFilterRequest,
    FileFlatFilterRequest,
    FileResponseModel,
    OrderingModel,
)
from app.schemas.file_management import (
    AliasDir,
    BatchFileResult,
    BatchFilesMoveRequest,
    BatchRemoveFilesRequest,
    DownloadArchiveRequestPayload,
    MakeDirCustomRequest,
    MakeDirRequest,
    MakeDirResponse,
    RenameFileRequest,
    RenameFileResponse,
    SaveFileRequest,
    UploadFileResponse,
)
from app.services.file_management.file_manager_service import FileManagerService
from app.services.media.music_file_service import MusicFileService
from app.util.atomic_write import atomic_write
from app.util.doc_util import build_response_description
from app.util.file_handlers import find_file_handler
from app.util.file_stream import stream_file_response
from app.util.file_util import (
    expand_home_dir,
    file_name_parent_directory,
    file_to_relative,
    resolve_absolute_path,
    zip_files_generator,
)
from app.util.mime_type_helper import guess_mime_type
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


router = APIRouter()
_log = Logger(__name__)

abs_file_name_query = Annotated[
    str,
    Query(
        ...,
        description="Absolute file path. Must start with '/' (for an absolute path) or '~/' (to refer to the home directory), followed by the path.",
        pattern=r"^(?:/|~/).+$",
    ),
]


alias_dir_param = Annotated[
    AliasDir, Path(description="Directory alias for application content")
]

relative_file_name_query = Annotated[
    str,
    Query(
        ...,
        min_length=1,
        description="The file's name (relative to its directory alias)",
    ),
]

manager = Annotated[FileManagerService, Depends(deps.get_directory_handler_by_alias)]

photo_file_manager_dep = Annotated[
    FileManagerService, Depends(deps.get_photo_file_manager)
]
video_file_manager_dep = Annotated[
    FileManagerService, Depends(deps.get_video_file_manager)
]
music_file_manager_dep = Annotated[
    MusicFileService, Depends(deps.get_music_file_service)
]
data_file_manager_dep = Annotated[
    FileManagerService, Depends(deps.get_data_file_manager)
]

global_file_manager_dep = Annotated[FileManager, Depends(deps.get_custom_file_manager)]

alias_handlers = Annotated[
    Dict[AliasDir, FileManagerService], Depends(deps.get_directory_handlers)
]


@router.post(
    "/files/upload",
    response_model=UploadFileResponse,
    response_description="A response describing the result of the file upload.",
    responses={
        400: {
            "description": "Bad Request. Invalid filename.",
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
async def upload_custom_file(
    request: Request,
    file: UploadFile = File(...),
    dir: str = Form(None),
    file_manager: "FileManager" = Depends(deps.get_custom_file_manager),
):
    """
    Upload a file to the specified directory.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    try:
        result = await asyncio.to_thread(file_manager.save_uploaded_file, file, dir)
        if result:
            await connection_manager.broadcast_json(
                {
                    "type": "uploaded",
                    "payload": [{"file": file.filename, "type": "files"}],
                }
            )
        return {"success": True, "filename": file.filename}
    except InvalidFileName:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    except Exception:
        _log.error("Unhandled exception during file upload", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload the file.")


@router.post(
    "/files/upload/{alias_dir}",
    response_model=UploadFileResponse,
    response_description="A response describing the result of the file upload.",
    responses={**upload_responses, **alias_dir_validation_error_response},
)
async def upload_file_in_aliased_dir(
    request: Request,
    alias_dir: alias_dir_param,
    manager: manager,
    file: UploadFile = File(...),
    dir: Optional[str] = Form(None),
):
    """
    Upload a file for the specified media type ('music', 'image', 'video', or 'data').
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    try:
        result = await asyncio.to_thread(manager.save_uploaded_file, file, dir)
        if result:
            await connection_manager.broadcast_json(
                {
                    "type": "uploaded",
                    "payload": [{"file": file.filename, "type": alias_dir}],
                }
            )
        return {"success": True, "filename": file.filename}
    except InvalidFileName:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    except Exception:
        _log.error("Unhandled exception during file upload", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload the file.")


@router.delete(
    "/files/remove",
    response_model=BatchFileResult,
    response_description="A response indicating the result of the removal operation.",
    responses=remove_file_responses,
)
async def remove_file(
    request: Request,
    filename: abs_file_name_query,
    handlers: alias_handlers,
    file_manager: global_file_manager_dep,
):
    """
    Remove a file for the specified media type.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    filename = expand_home_dir(filename)
    alias_dir, handler = find_file_handler(filename, handlers)

    _log.info("Removing file '%s'", filename)
    try:

        if handler:
            result = await asyncio.to_thread(
                handler.remove_file, file_to_relative(filename, handler.root_directory)
            )
        else:
            result = await asyncio.to_thread(file_manager.remove_file, filename)
        if result:
            await connection_manager.broadcast_json(
                {
                    "type": "removed",
                    "payload": [
                        {
                            "file": filename,
                            "type": alias_dir.value if alias_dir else "files",
                        }
                    ],
                }
            )
        return {"success": result, "filename": filename}
    except (ActiveMusicTrackRemovalError, DefaultFileRemoveAttempt) as e:
        _log.warning(str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        _log.warning("File %s not found", filename)
        raise HTTPException(status_code=404, detail="File not found")
    except InvalidFileName:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    except PermissionError as e:
        _log.error("Permission denied: %s", e)
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError:
        _log.error(
            "OS error while removing file '%s'",
            filename,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to remove '{filename}'")
    except Exception:
        _log.error(
            "Unhandled error while removing file '%s'",
            filename,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to remove '{filename}'")


@router.get(
    "/files/download",
    response_description="A file for download.",
    response_class=FileResponse,
    responses=download_file_responses,
)
def download_file(
    filename: abs_file_name_query,
):
    """
    Download a file.
    """
    filename = expand_home_dir(filename)

    try:
        basename = os.path.basename(filename)
        if not os.path.isfile(filename) and not os.path.isdir(filename):
            raise HTTPException(status_code=404, detail="Not a readable file")
        if not os.path.isdir(filename):
            guessed_mime_type = guess_mime_type(filename)
            return FileResponse(
                path=filename,
                media_type=guessed_mime_type or "application/octet-stream",
                filename=basename,
            )
        else:
            try:
                dir = file_name_parent_directory(filename).as_posix()
                directory_fn = lambda _: dir
                archive_name = f"{basename}.zip"
                _log.info(f"Created archive {archive_name}")
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
                _log.error(f"Error creating archive: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
    except FileNotFoundError:
        _log.warning("File %s not found", filename)
        raise HTTPException(status_code=404, detail="File not found")
    except InvalidFileName:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    except PermissionError as e:
        _log.error("Permission denied: %s", e)
        raise HTTPException(status_code=403, detail="Permission denied")
    except RuntimeError:
        _log.error("Runtime error while processing file '%s'", filename, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    except OSError:
        _log.error(
            "OS error while accessing file '%s'",
            filename,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to download '{filename}'")
    except Exception:
        _log.error(
            "Unhandled error '%s'",
            filename,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to download '{filename}'")


@router.get(
    "/files/download/{alias_dir}",
    response_description="A file for download.",
    response_class=FileResponse,
    responses={**download_file_responses, **alias_dir_validation_error_response},
)
def download_file_in_aliased_dir(
    filename: relative_file_name_query,
    manager: manager,
):
    """
    Download a file for the specified media type.
    """
    try:
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
                _log.info(f"Created archive {archive_name}")
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
                _log.error(f"Error creating archive: {e}")
                raise HTTPException(status_code=500, detail="Internal server error")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


@router.post(
    "/files/download/archive",
    response_description="A ZIP archive containing the requested files is delivered.",
    response_class=StreamingResponse,
    responses=download_archive_responses,
)
def download_custom_files_as_archive(
    payload: DownloadArchiveRequestPayload,
):
    """
    Download multiple files as a ZIP archive for the specified media type.
    """
    try:
        directory_fn = lambda f: file_name_parent_directory(f).as_posix()
        archive_name = payload.archive_name
        _log.info(f"Created archive {archive_name}")
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
        _log.error(f"Error creating archive: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/files/download/archive/{alias_dir}",
    response_description="A ZIP archive containing the requested files is delivered.",
    response_class=StreamingResponse,
    responses={**download_archive_responses, **alias_dir_validation_error_response},
)
def download_files_as_archive_from_aliased_dir(
    payload: DownloadArchiveRequestPayload,
    manager: manager,
):
    """
    Download multiple files as a ZIP archive for the specified media type.
    """
    try:
        directory_fn = lambda _: manager.root_directory
        archive_name = payload.archive_name
        _log.info(f"Created archive {archive_name}")
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
        _log.error(f"Error creating archive: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/files/preview-image",
    response_class=FileResponse,
    summary="Preview image by absolute filename",
    response_description="A preview image is returned.",
    responses=image_preview_responses,
)
def preview_image(
    filename: abs_file_name_query,
):
    """
    Return a preview image for the specified file.
    """

    filename = expand_home_dir(filename)

    try:
        return FileResponse(
            path=filename,
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
    "/files/preview-image/{alias_dir}",
    response_class=FileResponse,
    summary="Preview image in aliased directory",
    response_description="A preview image is returned.",
    responses={**image_preview_responses, **alias_dir_validation_error_response},
)
def preview_image_in_aliased_dir(
    filename: relative_file_name_query,
    manager: manager,
):
    """
    Return a preview image for the specified file.
    """
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
    "/files/preview-video/{alias_dir}",
    response_class=FileResponse,
    summary="Get an image poster for the video in aliased directory",
    response_description="An image poster for the video file is returned.",
    responses={**image_preview_responses, **alias_dir_validation_error_response},
)
def preview_video_in_aliased_dir(
    filename: relative_file_name_query,
    manager: manager,
):
    """
    Return a preview image for the specified video file.
    """
    try:
        full_path = manager.get_video_poster(filename)
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
    "/files/list",
    response_model=FileResponseModel,
    summary="List files with fuzzzy, searching, filtering and ordering.",
    response_description=build_response_description(FileResponseModel),
)
def list_files(
    request_data: FileFlatFilterRequest,
    file_manager: "FileManager" = Depends(deps.get_custom_file_manager),
):
    """
    Return a list of files for the specified media type.
    """

    try:
        result = file_manager.get_files_in_dir(
            root_dir=request_data.root_dir,
            filter_model=request_data.filters,
            search=request_data.search,
            ordering=request_data.ordering,
        )
        return result
    except PermissionError as e:
        _log.error("Permission denied: %s", e)
        raise HTTPException(status_code=403, detail="Permission denied")


@router.post(
    "/files/list/{alias_dir}",
    summary="Return a hierarchical files tree in the specified aliased directory.",
    response_description=build_response_description(FileResponseModel),
)
def list_files_in_aliased_dir(
    request_data: FileFilterRequest,
    manager: manager,
):
    """
    Return a list of files for the specified media type.
    """
    try:
        result = manager.get_files_tree(
            filter_model=request_data.filters,
            search=request_data.search,
            ordering=request_data.ordering,
            subdir=request_data.dir,
        )
        return result
    except PermissionError as e:
        _log.error("Permission denied: %s", e)
        raise HTTPException(status_code=403, detail="Permission denied")


@router.get(
    "/files/download-last-video",
    response_description="A response containing the most recent recorded video.",
    response_class=FileResponse,
    responses=download_video_responses,
)
def fetch_last_video(
    video_manager: Annotated[FileManagerService, Depends(deps.get_video_file_manager)]
):
    """
    Return the most recent video file.
    """
    result = video_manager.get_files_tree(ordering=OrderingModel())
    video_file: Optional[str] = None
    for file in result.data:
        if video_manager.is_video(file):
            video_file = os.path.join(video_manager.root_directory, file.path)
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
    "/files/remove-batch/{alias_dir}",
    response_model=List[BatchFileResult],
    summary="Remove a batch of files in a specified aliased directory",
    response_description="A list of responses indicating the result for each file's removal.",
    responses=alias_dir_validation_error_response,
)
async def batch_remove_in_aliased_dir(
    request: Request,
    alias_dir: alias_dir_param,
    request_body: BatchRemoveFilesRequest,
    manager: manager,
):
    """
    Remove multiple files for the specified media type.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    filenames = request_body.filenames
    if len(filenames) <= 0:
        raise HTTPException(status_code=400, detail="No files to remove!")
    excluded_files: List[BatchFileResult] = []
    responses, success_responses = await asyncio.to_thread(
        manager.batch_remove_files, filenames
    )
    success_responses: List[Dict[str, str]] = [
        {**item, "type": alias_dir} for item in success_responses
    ]
    if success_responses:
        await connection_manager.broadcast_json(
            {"type": "removed", "payload": success_responses}
        )
    return responses + excluded_files


@router.post(
    "/files/mkdir",
    response_model=MakeDirResponse,
)
async def make_dir(
    request_body: MakeDirCustomRequest,
):
    """
    Create a new directory.
    """
    filename = request_body.filename
    dir = request_body.root_dir

    file_path = pathlib.Path(os.path.join(dir, filename))
    await asyncio.to_thread(file_path.mkdir, parents=True)
    return {"success": file_path.exists(), "filename": filename}


@router.post(
    "/files/mkdir/{alias_dir}",
    response_model=MakeDirResponse,
    responses=alias_dir_validation_error_response,
)
async def mkdir_in_aliased_dir(
    request: Request,
    alias_dir: alias_dir_param,
    request_body: MakeDirRequest,
    manager: manager,
):
    """
    Create a new directory in the specified media type.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    filename = request_body.filename
    root_dir = manager.root_directory
    _log.info("Creating directory %s", filename)
    file_path = pathlib.Path(os.path.join(root_dir, filename))
    await asyncio.to_thread(file_path.mkdir, parents=True)
    await connection_manager.broadcast_json(
        {"type": "created", "payload": [{"type": alias_dir, "file": filename}]}
    )
    return {"success": file_path.exists(), "filename": filename}


@router.post(
    "/files/rename",
    response_model=RenameFileResponse,
)
async def rename_file(
    request: Request,
    request_body: RenameFileRequest,
    handlers: alias_handlers,
    file_manager: global_file_manager_dep,
):
    """
    Rename a file or directory for the specified media type.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager

    filename = request_body.filename
    new_name = request_body.new_name
    alias_dir, handler = find_file_handler(filename, handlers)
    _log.info("renaming filename %s to %s, alias_dir=%s", filename, new_name, alias_dir)
    try:
        if handler:
            await asyncio.to_thread(
                handler.rename_file,
                file_to_relative(filename, handler.root_directory),
                file_to_relative(new_name, handler.root_directory),
            )
        else:
            await asyncio.to_thread(
                file_manager.rename_file,
                filename,
                new_name,
            )

        _log.info("Renamed file")
        await connection_manager.broadcast_json(
            {
                "type": "renamed",
                "payload": [
                    {
                        "type": alias_dir.value if alias_dir else "files",
                        "file": filename,
                    }
                ],
            }
        )
        _log.info("New name exists")
        return {
            "success": os.path.exists(new_name),
            "error": None,
            "filename": filename,
            "new_name": new_name,
        }
    except FileNotFoundError as e:
        _log.error("Failed to rename file: %s", e)
        raise HTTPException(status_code=404, detail="File not found")
    except InvalidFileName:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    except PermissionError as e:
        _log.error("Permission denied: %s", e)
        raise HTTPException(status_code=403, detail="Permission denied")
    except OSError:
        _log.error(
            "OS error while renaming file '%s' to '%s'",
            filename,
            new_name,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to rename '{filename}' to '{new_name}'"
        )
    except Exception:
        _log.error(
            "Unhandled error while renaming file '%s' to '%s'",
            filename,
            new_name,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to rename '{filename}' to '{new_name}'"
        )


@router.post(
    "/files/move",
    response_model=List[BatchFileResult],
)
async def move_files(
    request: Request,
    request_body: BatchFilesMoveRequest,
    file_manager: "FileManager" = Depends(deps.get_custom_file_manager),
):
    """
    Move multiple files or directories within the specified media type.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    responses, success_responses = await asyncio.to_thread(
        file_manager.batch_move_files, request_body.filenames, request_body.dir
    )
    success_responses: List[Dict[str, str]] = [
        {**item, "type": "files"} for item in success_responses
    ]
    if success_responses:
        await connection_manager.broadcast_json(
            {"type": "moved", "payload": success_responses}
        )
    return responses


@router.post(
    "/files/move/{alias_dir}",
    response_model=List[BatchFileResult],
    responses=alias_dir_validation_error_response,
)
async def move_files_in_aliased_dir(
    request: Request,
    alias_dir: alias_dir_param,
    manager: manager,
    request_body: BatchFilesMoveRequest,
):
    """
    Move multiple files or directories within the specified media type.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    responses, success_responses = await asyncio.to_thread(
        manager.batch_move_files, request_body.filenames, request_body.dir
    )
    success_responses: List[Dict[str, str]] = [
        {**item, "type": alias_dir} for item in success_responses
    ]
    if success_responses:
        await connection_manager.broadcast_json(
            {"type": "moved", "payload": success_responses}
        )
    return responses


@router.put(
    "/files/write/{alias_dir}",
    response_model=SaveFileRequest,
    responses=write_file_responses,
)
def write_file_in_aliased_dir(
    payload: SaveFileRequest,
    manager: manager,
):
    """
    Save or update the content of a file.
    """
    try:
        dir = (
            resolve_absolute_path(payload.dir, manager.root_directory)
            if payload.dir
            else manager.root_directory
        )

        full_path = resolve_absolute_path(payload.path, dir)
        _log.info(
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


@router.put(
    "/files/write",
    response_model=SaveFileRequest,
    responses=write_file_responses,
)
def write_file(
    payload: SaveFileRequest,
):
    """
    Save or update the content of a file.
    """
    try:
        full_path = resolve_absolute_path(payload.path, payload.dir)
        _log.info(
            "Writing the file %s, payload.dir %s",
            full_path,
            payload.dir,
        )
        with atomic_write(full_path, mode="w") as f:
            f.write(payload.content)
        return payload
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Error writing file: {ex}")


@router.get(
    "/files/video-stream/{alias_dir}",
    response_class=StreamingResponse,
    responses={**video_stream_responses, **alias_dir_validation_error_response},
)
def stream_video_in_aliased_dir(
    alias_dir: alias_dir_param,
    filename: relative_file_name_query,
    manager: manager,
    range_header: Optional[str] = Header(None),
):
    """
    Stream a video file with support for partial content.
    """
    _log.info("Streaming video %s, alias_dir=%s", filename, alias_dir)
    try:
        file_path = manager.convert_video_for_streaming(filename)
        if file_path is None:
            raise HTTPException(status_code=503, detail="Failed to stream file")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")

    video_media_types = {
        "mp4": "video/mp4",
        "avi": "video/x-msvideo",
        "mov": "video/quicktime",
        "mkv": "video/x-matroska",
    }
    return stream_file_response(file_path, video_media_types, range_header)


@router.get(
    "/files/audio-stream/{alias_dir}",
    response_class=StreamingResponse,
    responses={**audio_stream_responses, **alias_dir_validation_error_response},
)
def stream_audio_in_aliased_dir(
    alias_dir: alias_dir_param,
    filename: relative_file_name_query,
    manager: manager,
    range_header: Optional[str] = Header(None),
):
    """
    Stream an audio file with support for partial content.
    """
    _log.info("Streaming audio %s, alias_dir=%s", filename, alias_dir)
    audio_path = resolve_absolute_path(filename, manager.root_directory)

    audio_media_types = {
        "mp3": "audio/mpeg",
        "ogg": "audio/ogg",
        "wav": "audio/wav",
    }
    return stream_file_response(audio_path, audio_media_types, range_header)
