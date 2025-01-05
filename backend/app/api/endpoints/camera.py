from time import localtime, strftime
from typing import TYPE_CHECKING

from app.api import deps
from app.api.endpoints.devices_mock import mocked_devices
from app.exceptions.camera import CameraDeviceError, CameraNotFoundError
from app.schemas.camera import CameraDevicesResponse, CameraSettings, PhotoResponse
from app.util.logger import Logger
from app.util.photo import capture_photo
from app.util.v4l2_manager import V4L2
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.services.camera_service import CameraService
    from app.services.connection_service import ConnectionService
    from app.services.file_service import FileService

router = APIRouter()
logger = Logger(__name__)


@router.post(
    "/camera/settings",
    response_model=CameraSettings,
    tags=["camera"],
    summary="Update camera settings",
    response_description="**Settings:**"
    "\n"
    "- **device**: ID or name of the camera device."
    "\n"
    "- **width**: Frame width in pixels."
    "\n"
    "- **height**: Frame height in pixels."
    "\n"
    "- **fps**: Frames per second for capturing."
    "\n"
    "- **pixel_format**: Pixel format, such as 'RGB' or 'GRAY'."
    "\n",
)
async def update_camera_settings(
    request: Request,
    payload: CameraSettings,
    camera_manager: "CameraService" = Depends(deps.get_camera_manager),
):
    """
    Update the camera settings with new configurations and broadcast the updates.

    This endpoint updates the camera's configurations (e.g., resolution, FPS, pixel format),
    handling retries when the specified device fails, and broadcasts the updated settings
    or errors to connected clients.

    Broadcast Behavior:
    --------------
    - **On Success**: The successfully updated camera settings are broadcast via
      `connection_manager.broadcast_json` to ensure all connected clients are up-to-date.
    - **On Device Retry**: If the incoming payload specifies a `device` that fails
      initialization, the service attempts to find and configure an alternate available device.
      In such cases, the `self.camera_settings.device` may be updated to reflect the new device.
      This updated value, along with the other camera settings, will then be broadcast.
    - **On Failure**: If the update fails entirely (e.g., due to an invalid device or other issues),
      an error message is broadcast to clients via the `connection_manager.error` channel.
      Additionally, the current state of the camera settings (including any partial changes,
      such as a modified `self.camera_settings.device` due to retries) is broadcast.

    Workflow:
    --------------
    1. Accepts new camera settings via the `payload`.
    2. Updates `self.camera_settings` with validated changes.
    3. If the specified `device` fails initialization:
       - Attempts to find and configure another device.
       - Updates `self.camera_settings.device` if a different device is chosen.
    4. Broadcasts the final `self.camera_settings` to clients, regardless of success or failure.
    5. In the case of errors, also broadcasts an error message to clients.

    Returns:
    --------------
    - `CameraSettings`: The updated camera settings.

    - Additionally, broadcasts the updated settings to all connected clients.
    """
    logger.info("Camera update payload %s", payload)
    connection_manager: "ConnectionService" = request.app.state.app_manager
    try:
        result = await camera_manager.update_camera_settings(payload)
        await connection_manager.broadcast_json(
            {"type": "camera", "payload": result.model_dump()}
        )
        return result
    except (CameraDeviceError, CameraNotFoundError) as err:
        await connection_manager.broadcast_json(
            {"type": "camera", "payload": camera_manager.camera_settings.model_dump()}
        )
        await connection_manager.error(str(err))
        raise HTTPException(
            status_code=400, detail=f"Couldn't update camera settings: {str(err)}"
        )
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
    tags=["camera"],
    summary="Get camera settings",
    response_description="**Settings:**"
    "\n"
    "- **device**: ID or name of the camera device."
    "\n"
    "- **width**: Frame width in pixels."
    "\n"
    "- **height**: Frame height in pixels."
    "\n"
    "- **fps**: Frames per second for capturing."
    "\n"
    "- **pixel_format**: Pixel format, such as 'RGB' or 'GRAY'."
    "\n",
)
def get_camera_settings(
    camera_manager: "CameraService" = Depends(deps.get_camera_manager),
):
    """
    Retrieve the current camera settings.

    Returns:
    --------------
    `CameraSettings`: Current camera configuration data.
    """
    return camera_manager.camera_settings


@router.get(
    "/camera/devices",
    response_model=CameraDevicesResponse,
    summary="Retrieve a list of available camera devices",
)
def get_camera_devices():
    """
    Retrieve a list of available camera devices.

    This endpoint identifies primary and secondary camera devices based on categorized
    rules and available video devices in the system.

    Returns:
    --------------
    `CameraDevicesResponse`: A structured list of available camera devices.
    """
    devices = V4L2.list_video_devices_with_formats()
    return {"devices": devices + mocked_devices}


@router.get(
    "/camera/capture-photo",
    response_model=PhotoResponse,
    summary="Capture a photo",
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
    camera_manager: "CameraService" = Depends(deps.get_camera_manager),
    file_manager: "FileService" = Depends(deps.get_file_manager),
):
    """
    Capture a photo using the camera and save it to the specified file location.

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
    raise HTTPException(status_code=400, detail="Error capturing photo")
