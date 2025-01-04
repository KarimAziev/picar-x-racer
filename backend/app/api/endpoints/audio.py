import asyncio
from typing import TYPE_CHECKING

from app.api import deps
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
    "/audio/volume",
    response_model=VolumeData,
    summary="Set the playback volume to the specified level.",
    response_description="The volume level is returned as a normalized integer between 0 and 100.",
    responses={
        404: {
            "description": "Not Found. `amixer` is missing.",
            "content": {
                "application/json": {
                    "example": {"detail": "'amixer' is not installed on the system."}
                }
            },
        },
        503: {
            "description": "Service Unavailable. General audio issue.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Error setting the volume due to a command execution failure."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error. This error occurs if something unexpected breaks during processing.",
            "content": {
                "application/json": {"example": {"detail": "Failed to set the volume."}}
            },
        },
        422: {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "value_error",
                                "loc": ["body", "volume"],
                                "msg": "Value error, Volume decimal precision must be at most 1.",
                                "input": 76.43,
                                "ctx": {
                                    "error": {},
                                },
                            },
                        ]
                    }
                }
            },
        },
    },
)
async def set_volume(
    request: Request,
    payload: VolumeData,
    audio_manager: "AudioService" = Depends(deps.get_audio_manager),
):
    """
    Set the playback volume level.

    This endpoint allows the client to set the playback volume level. It also notifies all
    connected WebSocket clients about the volume change.

    Behavior:
    --------------
    The input should specify the `volume` level, either as an integer or a float.

    Floats are automatically normalized to integers (e.g., `45.6` becomes `46`).

    The accepted range is 0 to 100; values outside this range will raise an error.

    All responses will return the `volume` as a normalized integer.

    Returns:
    --------------
    **VolumeData**: The updated volume level (as an integer).

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
    except AmixerNotInstalled as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AudioVolumeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.error("Unexpected error while getting the volume level", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to set the volume.")


@router.get(
    "/audio/volume",
    response_model=VolumeData,
    summary="Retrieve the current volume level",
    response_description="The volume level is returned as a normalized integer between 0 and 100.",
    responses={
        404: {
            "description": "Not Found. `amixer` is missing.",
            "content": {
                "application/json": {
                    "example": {"detail": "'amixer' is not installed on the system."}
                }
            },
        },
        503: {
            "description": "Service Unavailable. General audio fetching issue.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Error getting the volume due to a command execution failure."
                    }
                }
            },
        },
        500: {
            "description": "Internal Server Error. This error occurs if something unexpected breaks during processing.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to retrieve volume information."}
                }
            },
        },
    },
)
async def get_volume(
    audio_manager: "AudioService" = Depends(deps.get_audio_manager),
):
    """
    Retrieve the current playback volume level.

    This endpoint allows the client to retrieve the current volume level of the playback device.

    Behavior:
    --------------
    The volume level is returned as a normalized integer between 0 and 100.
    Floats are not involved in this endpoint, as the volume is always computed and stored as integers.

    Returns:
    --------------
    **VolumeData**: The current volume level (as an integer).
    """
    try:
        current_volume = await asyncio.to_thread(audio_manager.get_volume)
        return {"volume": current_volume}
    except AmixerNotInstalled as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AudioVolumeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.error("Unexpected error while getting the volume level", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve volume information."
        )


@router.websocket("/ws/audio-stream")
async def audio_stream_ws(
    websocket: WebSocket,
    audio_service: "AudioStreamService" = Depends(deps.get_audio_stream_service),
):
    """
    WebSocket endpoint for providing audio stream to a client.
    """
    await audio_service.audio_stream_to_ws(websocket)
