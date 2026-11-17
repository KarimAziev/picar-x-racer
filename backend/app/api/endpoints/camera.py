"""
Endpoints for camera operations, including configuring the device and capturing photos.
"""

import asyncio
from datetime import datetime
from uuid import uuid4
from typing import TYPE_CHECKING, Annotated

from app.api import deps
from app.config.video_enhancers import frame_enhancers
from app.core.gstreamer_parser import GStreamerParser
from app.core.logger import Logger
from app.exceptions.camera import (
    CameraBusyError,
    CameraDeviceError,
    CameraNotFoundError,
    CameraShutdownInProgressError,
)
from app.schemas.camera import CameraDevicesResponse, CameraSettings, PhotoResponse
from app.schemas.photo import PhotoCaptureRequest, PhotoSettings
from app.schemas.camera_controls import CameraControlCapabilities
from app.exceptions.detection import DetectionProcessError
from app.types.detection import DetectionQueueData, DetectionResultData
from app.util.doc_util import build_response_description
from app.util.photo import capture_photo, prepare_photo_frame
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.adapters.video_device_adapter import VideoDeviceAdapter
    from app.services.camera.camera_service import CameraService
    from app.services.camera.gstreamer_service import GStreamerService
    from app.services.connection_service import ConnectionService
    from app.services.detection.detection_service import DetectionService
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

    api, device_path = GStreamerParser.parse_device_path(payload.device or "")
    gstreamer_supported = api in (None, "v4l2", "libcamera") or device_path.startswith(
        "/dev/video"
    )

    if (
        payload.use_gstreamer
        and gstreamer_supported
        and not gstreamer_manager.gstreamer_available()
    ):
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


@router.get("/camera/controls", response_model=CameraControlCapabilities)
async def get_camera_controls(
    device: str,
    camera_manager: Annotated["CameraService", Depends(deps.get_camera_service)],
):
    """Inspect supported exposure and focus modes without changing their values."""
    try:
        return await asyncio.to_thread(camera_manager.get_control_capabilities, device)
    except (CameraDeviceError, CameraNotFoundError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post(
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
    detection_service: Annotated[
        "DetectionService", Depends(deps.get_detection_service)
    ],
    file_manager: Annotated["FileManagerService", Depends(deps.get_photo_file_manager)],
    payload: PhotoCaptureRequest | None = None,
):
    """
    Capture a photo using the camera and save it to the specified file location.
    """
    if payload and payload.preset_id:
        settings = PhotoSettings.model_validate(
            camera_manager.file_manager.settings.get("photo", {})
        )
        preset = next(
            (item for item in settings.presets if item.id == payload.preset_id), None
        )
        if preset is None:
            raise HTTPException(status_code=404, detail="Photo preset not found")
        try:
            frame = await camera_manager.capture_preset_photo(preset)
        except CameraBusyError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except CameraShutdownInProgressError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except (CameraDeviceError, CameraNotFoundError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        photo_detection = None
        photo_detection_settings = None
        if (
            camera_manager.stream_settings.include_detection_overlay_in_media
            and detection_service.detection_settings.active
        ):
            try:
                photo_detection_settings, photo_detection = (
                    await detection_service.detect_photo(frame)
                )
            except DetectionProcessError as error:
                raise HTTPException(status_code=503, detail=str(error)) from error

        enhancer = (
            frame_enhancers.get(preset.enhance_mode) if preset.enhance_mode else None
        )
        if enhancer:
            frame = await asyncio.to_thread(enhancer, frame)
        frame = await asyncio.to_thread(
            prepare_photo_frame,
            frame,
            preset.rotation,
            detection_settings=photo_detection_settings,
            detection_state=photo_detection,
            frame_timestamp=(
                photo_detection["timestamp"] if photo_detection is not None else None
            ),
            render_detection_overlay=photo_detection is not None,
        )
        name = (
            f"photo_{datetime.now():%Y-%m-%d-%H-%M-%S}_{uuid4().hex[:8]}{preset.format}"
        )
        status = await capture_photo(
            img=frame,
            photo_name=name,
            path=file_manager.root_directory,
            quality=preset.quality,
        )
        if not status:
            raise HTTPException(status_code=400, detail="Error saving photo")
        return {"file": name}

    if camera_manager.photo_capturing:
        raise HTTPException(status_code=409, detail="A photo capture is in progress")
    name = f"photo_{datetime.now():%Y-%m-%d-%H-%M-%S}_{uuid4().hex[:8]}.jpg"
    rotation = camera_manager.stream_settings.rotation

    frame = (
        camera_manager.stream_img
        if camera_manager.stream_img is not None
        else camera_manager.img
    )

    if frame is None:
        raise HTTPException(status_code=503, detail="Camera is not ready")

    detection_state: DetectionResultData | DetectionQueueData | None = None
    if detection_service.detection_settings.active:
        detection_service.poll_detection_result()
        detection_state = detection_service.current_state

    frame = prepare_photo_frame(
        frame=frame,
        rotation=rotation,
        detection_settings=detection_service.detection_settings,
        detection_state=detection_state,
        frame_timestamp=camera_manager.current_frame_timestamp,
        render_detection_overlay=(
            camera_manager.stream_settings.include_detection_overlay_in_media
        ),
    )

    status = await capture_photo(
        img=frame,
        photo_name=name,
        path=file_manager.root_directory,
    )
    if status:
        return {"file": name}
    raise HTTPException(status_code=400, detail="Error capturing photo")
