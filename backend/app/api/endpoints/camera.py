"""
Endpoints for camera operations, including configuring the device and capturing photos.
"""

from time import localtime, strftime
from typing import TYPE_CHECKING, Annotated

import cv2
import numpy as np
from app.api import deps
from app.core.logger import Logger
from app.exceptions.camera import (
    CameraDeviceError,
    CameraNotFoundError,
    CameraShutdownInProgressError,
)
from app.schemas.camera import CameraDevicesResponse, CameraSettings, PhotoResponse
from app.schemas.stream import ImageRotation
from app.util.doc_util import build_response_description
from app.util.photo import capture_photo
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.adapters.video_device_adapter import VideoDeviceAdapter
    from app.services.camera.camera_service import CameraService
    from app.services.camera.gstreamer_service import GStreamerService
    from app.services.connection_service import ConnectionService
    from app.services.file_management.file_manager_service import FileManagerService

router = APIRouter()
_log = Logger(__name__)


@router.post(
    "/camera/settings",
    response_model=CameraSettings,
    response_description=build_response_description(
        CameraSettings, "Updated settings with the such fields:"
    ),
    summary="Update camera settings",
)
async def update_camera_settings(
    request: Request,
    payload: CameraSettings,
    camera_manager: Annotated["CameraService", Depends(deps.get_camera_service)],
    gstreamer_manager: Annotated[
        "GStreamerService", Depends(deps.get_gstreamer_service)
    ],
):
    """
    Update the camera settings with new configurations and broadcast the updates.

    This endpoint updates the camera's configurations (e.g., resolution, FPS, pixel format),
    handling retries when the specified device fails, and broadcasts the updated settings
    or errors to connected clients.
    """
    _log.info("Camera update payload %s", payload)
    connection_manager: "ConnectionService" = request.app.state.app_manager

    if payload.use_gstreamer and not gstreamer_manager.gstreamer_available():
        reason = "'gst-launch-1.0' is not found in PATH"
        msg = f"GStreamer will not be used, because {reason}."
        _log.warning(msg)
        raise HTTPException(status_code=400, detail=msg)

    try:
        result = await camera_manager.update_camera_settings(payload)
        await connection_manager.broadcast_json(
            {"type": "camera", "payload": result.model_dump()}
        )
        await camera_manager.notify_camera_error(camera_manager.camera_device_error)
        return result
    except (CameraDeviceError, CameraNotFoundError) as err:
        await connection_manager.broadcast_json(
            {"type": "camera", "payload": camera_manager.camera_settings.model_dump()}
        )
        await connection_manager.error(str(err))
        raise HTTPException(status_code=400, detail=str(err))
    except CameraShutdownInProgressError as err:
        raise HTTPException(status_code=503, detail=str(err))
    except Exception as err:
        await connection_manager.broadcast_json(
            {"type": "camera", "payload": camera_manager.camera_settings.model_dump()}
        )
        await connection_manager.error(str(err))
        raise HTTPException(
            status_code=500, detail=f"Unexpected camera error: {str(err)}"
        )


@router.get(
    "/camera/settings",
    response_model=CameraSettings,
    summary="Get camera settings",
    response_description=build_response_description(
        CameraSettings, "Current camera configuration data:"
    ),
)
def get_camera_settings(
    camera_manager: Annotated["CameraService", Depends(deps.get_camera_service)],
):
    """
    Retrieve the current camera settings.
    """
    return camera_manager.camera_settings


@router.get(
    "/camera/devices",
    response_model=CameraDevicesResponse,
    summary="Retrieve a list of available camera devices",
    response_description=build_response_description(
        CameraDevicesResponse, "Available camera devices."
    ),
)
def get_camera_devices(
    video_device_adapter: Annotated[
        "VideoDeviceAdapter", Depends(deps.get_video_device_adapter)
    ],
):
    """
    Retrieve a list of available camera devices.

    This endpoint identifies primary and secondary camera devices based on categorized
    rules and available video devices in the system.
    """
    try:
        devices = video_device_adapter.list_devices()
        return {"devices": devices}
    except Exception:
        _log.error("Unexpected error while listing camera devices", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list camera devices")


@router.get(
    "/camera/capture-photo",
    response_model=PhotoResponse,
    summary="Capture a photo",
    response_description=build_response_description(PhotoResponse),
    responses={
        400: {
            "description": "Raised if the photo could not be taken or saved due to an error",
            "content": {
                "application/json": {"example": {"detail": "Error capturing photo"}}
            },
        }
    },
)
async def take_photo(
    camera_manager: Annotated["CameraService", Depends(deps.get_camera_service)],
    file_manager: Annotated["FileManagerService", Depends(deps.get_photo_file_manager)],
):
    """
    Capture a photo using the camera and save it to the specified file location.
    """
    _time = strftime("%Y-%m-%d-%H-%M-%S", localtime())
    name = f"photo_{_time}.jpg"
    rotation = camera_manager.stream_settings.rotation

    frame = (
        camera_manager.stream_img
        if camera_manager.stream_img is not None
        else camera_manager.img
    )

    if rotation == ImageRotation.rotate_90:
        frame = cv2.rotate(np.ascontiguousarray(frame), cv2.ROTATE_90_CLOCKWISE)
    elif rotation == ImageRotation.rotate_180:
        frame = cv2.rotate(np.ascontiguousarray(frame), cv2.ROTATE_180)
    elif rotation == ImageRotation.rotate_270:
        frame = cv2.rotate(np.ascontiguousarray(frame), cv2.ROTATE_90_COUNTERCLOCKWISE)

    if frame is None:
        raise HTTPException(status_code=503, detail="Camera is not ready")

    status = (
        await capture_photo(
            img=frame.copy(),
            photo_name=name,
            path=file_manager.root_directory,
        )
        if camera_manager.img is not None
        else False
    )
    if status:
        return {"file": name}
    raise HTTPException(status_code=400, detail="Error capturing photo")
