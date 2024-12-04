import asyncio
from time import localtime, strftime
from typing import TYPE_CHECKING

from app.api.deps import get_camera_manager, get_file_manager
from app.schemas.camera import CameraDevicesResponse, CameraSettings, PhotoResponse
from app.util.device import list_available_camera_devices
from app.util.logger import Logger
from app.util.photo import capture_photo
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.services.camera_service import CameraService
    from app.services.connection_service import ConnectionService
    from app.services.files_service import FilesService

router = APIRouter()
logger = Logger(__name__)


@router.post(
    "/api/camera/settings",
    response_model=CameraSettings,
    tags=["camera"],
    summary="Update camera settings",
)
async def update_camera_settings(
    request: Request,
    payload: CameraSettings,
    camera_manager: "CameraService" = Depends(get_camera_manager),
):
    """
    Update the camera settings.

    Example Payload:
    --------------
    ```json
    {
        "device": "/dev/video0",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "pixel_format": "MJPEG"
    }
    ```


    Args:
    --------------
    - `request` (Request): FastAPI request object used to access app state and components.
    - `payload` (CameraSettings): New camera settings to apply.
    - `camera_manager` (CameraService): Camera management service for handling operations.

    Returns:
    --------------
    - `CameraSettings`: The updated camera settings.

    - Additionally, broadcasts the updated settings to all connected clients.

    Raises:
    --------------
    None
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    result: CameraSettings = await asyncio.to_thread(
        camera_manager.update_camera_settings, payload
    )
    await connection_manager.broadcast_json(
        {"type": "camera", "payload": result.model_dump()}
    )
    return result


@router.get(
    "/api/camera/settings",
    response_model=CameraSettings,
    tags=["camera"],
    summary="Get camera settings",
    response_description="""
    Settings:
    device: ID or name of the camera device.
    width: Frame width in pixels.
    height: Frame height in pixels.
    fps: Frames per second for capturing.
    pixel_format: Pixel format, such as 'RGB' or 'GRAY'.
    """,
)
def get_camera_settings(
    camera_manager: "CameraService" = Depends(get_camera_manager),
):
    """
    Retrieve the current camera settings.

    Example Response:
    --------------
    ```json
    {
        "device": "/dev/video0",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "pixel_format": "MJPEG"
    }
    ```

    Args:
    --------------
    - `camera_manager` (CameraService): Camera management service for retrieving settings.

    Returns:
    --------------
    `CameraSettings`: Current camera configuration data.
    """
    return camera_manager.camera_settings


@router.get(
    "/api/camera/devices",
    response_model=CameraDevicesResponse,
    summary="Retrieve a list of available camera devices",
)
def get_camera_devices():
    """
    Retrieve a list of available camera devices.

    This endpoint identifies primary and secondary camera devices based on categorized
    rules and available video devices in the system.

    Example Response:
    --------------
    ```json
    {
        "devices": [
            {
                "key": "/dev/video0",
                "label": "/dev/video0 (Primary Camera)",
                "selectable": False,
                "children": [
                    {"key": "MJPEG", "label": "MJPEG (1920x1080)"},
                    {"key": "YUYV", "label": "YUYV (640x480)"}
                ]
            },
            {
                "key": "/dev/video1",
                "label": "/dev/video1 (Secondary Camera)",
                "selectable": False,
                "children": [
                    {"key": "H264", "label": "H264 (1280x720)"}
                ]
            }
        ]
    }
    ```

    Returns:
    --------------
    `CameraDevicesResponse`: A structured list of available camera devices.
    """
    devices = list_available_camera_devices()
    return {"devices": devices}


@router.get(
    "/api/camera/capture-photo", response_model=PhotoResponse, summary="Capture a photo"
)
async def take_photo(
    camera_manager: "CameraService" = Depends(get_camera_manager),
    file_manager: "FilesService" = Depends(get_file_manager),
):
    """
    Capture a photo using the camera and save it to the specified file location.

    Args:
    --------------
    - `camera_manager` (CameraService): Camera management service for interfacing with the hardware.
    - `file_manager` (FilesService): File management service for determining save locations.

    Returns:
    --------------
    `PhotoResponse`: A response containing the filename of the captured photo.

    Raises:
    --------------
    `HTTPException (400)`: Raised if the photo could not be taken or saved due to an error.
    """
    _time = strftime("%Y-%m-%d-%H-%M-%S", localtime())
    name = f"photo_{_time}.jpg"

    await camera_manager.start_camera_and_wait_for_stream_img()

    status = (
        await capture_photo(
            img=camera_manager.img.copy(),
            photo_name=name,
            path=file_manager.user_photos_dir,
        )
        if camera_manager.img is not None
        else False
    )
    if status:
        return {"file": name}
    raise HTTPException(status_code=400, detail="Couldn't take photo")
