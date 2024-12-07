import asyncio
from typing import TYPE_CHECKING

from app.api.deps import get_audio_manager, get_audio_stream_service
from app.exceptions.audio import AmixerNotInstalled, AudioVolumeError
from app.schemas.audio import VolumeData
from app.util.logger import Logger
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket

if TYPE_CHECKING:
    from app.services.audio_service import AudioService
    from app.services.audio_stream_service import AudioStreamService
    from app.services.connection_service import ConnectionService

router = APIRouter()
logger = Logger(__name__)


@router.post(
    "/api/audio/volume",
    response_model=VolumeData,
    summary="Set the playback volume level",
)
async def set_volume(
    request: Request,
    payload: VolumeData,
    audio_manager: "AudioService" = Depends(get_audio_manager),
):
    """
    Set the playback volume level.

    This endpoint allows the client to set the playback volume level. It also notifies all
    connected WebSocket clients about the volume change.

    Behavior:
    --------------
    - The input should specify the `volume` level, either as an integer or a float.
    - Floats are automatically normalized to integers (e.g., `45.6` becomes `46`).
    - The accepted range is 0 to 100; values outside this range will raise an error.
    - All responses will return the `volume` as a normalized integer.

    Args:
    --------------
    - `request` (Request): The incoming HTTP request object.
    - `payload` (VolumeData): The desired volume level provided by the client.
    - `audio_manager` (AudioService): Dependency injection of the AudioService instance.

    Returns:
    --------------
    - `VolumeData`: The updated volume level (as an integer).

    Raises:
    --------------
    - `HTTPException` (500): If `amixer` is not installed on the system.
    - `HTTPException` (400): If there is an error while setting the volume.
    - `HTTPException` (500): If an unexpected error occurs.

    Example Request:
    --------------
    ```
    POST /api/volume
    Content-Type: application/json

    {
        "volume": 45.6
    }
    ```

    Example Response:
    --------------
    ```
    200 OK
    {
        "volume": 46
    }
    ```
    """
    logger.info("Volume update payload %s", payload)
    connection_manager: "ConnectionService" = request.app.state.app_manager
    volume = payload.volume
    int_volume = int(volume)
    try:
        await asyncio.to_thread(audio_manager.set_volume, int_volume)
        new_volume = await asyncio.to_thread(audio_manager.get_volume)

        try:
            await connection_manager.broadcast_json(
                {"type": "volume", "payload": new_volume}
            )
        except Exception as ws_err:
            logger.error(f"WebSocket broadcasting error: {ws_err}", exc_info=True)

        return {"volume": new_volume}
    except AmixerNotInstalled:
        logger.warning("'amixer' is not installed on the system.")
        raise HTTPException(
            status_code=500, detail="'amixer' is not installed on the system!"
        )
    except AudioVolumeError:
        logger.error("Error occurred while setting the volume.")
        raise HTTPException(
            status_code=400, detail="Error occurred while setting the volume level!"
        )
    except Exception as err:
        logger.error(f"Unexpected error in set_volume: {err}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your request.",
        )


@router.get(
    "/api/audio/volume",
    response_model=VolumeData,
    summary="Retrieve the current volume level",
)
async def get_volume(
    audio_manager: "AudioService" = Depends(get_audio_manager),
):
    """
    Retrieve the current playback volume level.

    This endpoint allows the client to retrieve the current volume level of the playback device.

    Behavior:
    --------------
    - The volume level is returned as a normalized integer between 0 and 100.
    - Floats are not involved in this endpoint, as the volume is always computed and stored as integers.

    Args:
    --------------
    - `audio_manager` (AudioService): Dependency injection of the AudioService instance.

    Returns:
    --------------
    - `VolumeData`: The current volume level (as an integer).

    Raises:
    --------------
    - `HTTPException` (500): If `amixer` is not installed on the system.
    - `HTTPException` (400): If there is an error while retrieving the volume level.
    - `HTTPException` (500): If an unexpected error occurs.

    Example Response:
    --------------
    ```
    200 OK
    {
        "volume": 75
    }
    ```
    """
    try:
        current_volume = await asyncio.to_thread(audio_manager.get_volume)
        if isinstance(current_volume, str):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve volume information: {current_volume}",
            )
        return {"volume": current_volume}
    except AmixerNotInstalled:
        raise HTTPException(
            status_code=404, detail="'amixer' is not installed on the system!"
        )
    except AudioVolumeError:
        raise HTTPException(
            status_code=404, detail="Error occurred while setting the volume level!"
        )
    except Exception as err:
        logger.error(f"Unexpected error in get_volume: {err}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(err))


@router.websocket("/ws/audio-stream")
async def audio_stream_ws(
    websocket: WebSocket,
    audio_service: "AudioStreamService" = Depends(get_audio_stream_service),
):
    """
    WebSocket endpoint for providing audio stream to a client.
    """
    await audio_service.audio_stream_to_ws(websocket)
