import asyncio
from os import path
from typing import TYPE_CHECKING

from app.api.deps import get_audio_manager, get_file_manager
from app.schemas.audio import (
    PlaySoundItem,
    PlaySoundResponse,
    PlayTTSItem,
    PlayTTSResponse,
    VolumeRequest,
    VolumeResponse,
)
from app.util.logger import Logger
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.services.audio_service import AudioService
    from app.services.connection_service import ConnectionService
    from app.services.files_service import FilesService

router = APIRouter()
logger = Logger(__name__)


@router.post(
    "/api/play-sound", response_model=PlaySoundResponse, summary="Play a sound"
)
async def play_sound(
    payload: PlaySoundItem,
    file_manager: "FilesService" = Depends(get_file_manager),
    audio_manager: "AudioService" = Depends(get_audio_manager),
):
    """
    Endpoint to play a sound.

    Args:

    - payload (PlaySoundItem): Contains the track details for the sound to be played.
    - file_manager (FilesService): The file service for managing files.
    - audio_manager (AudioService): The audio service for managing audio playback.

    Returns:
        `PlaySoundResponse`: The response object containing the play sound result.

    Raises:

    - HTTPException (400): If the track filename is invalid.
    - HTTPException (404): If the track file is not found.
    - HTTPException (500): If there is an error while playing the sound.
    """
    filename = payload.track

    force = payload.force if payload.force is not None else False
    if not isinstance(filename, str):
        raise HTTPException(status_code=400, detail="Invalid settings format")

    logger.info(f"Request to play sound {filename}")
    try:
        dir = file_manager.get_sound_directory(filename)
        file = path.join(dir, filename)
        result = audio_manager.play_sound(file, force)
        return result
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/api/play-tts", response_model=PlayTTSResponse)
async def text_to_speech(
    request: Request,
    payload: PlayTTSItem,
    audio_manager: "AudioService" = Depends(get_audio_manager),
):
    """
    Endpoint to convert text to speech.

    Args:
    - payload (PlayTTSItem): Contains the text and language details for text-to-speech conversion.
    - audio_manager (AudioService): The audio service for managing audio playback.

    Returns:
    - `PlayTTSResponse`: The response object containing the text and language used for TTS.

    Raises:
    - HTTPException (404): If Google speech is not available.
    """
    if not audio_manager.google_speech_available:
        raise HTTPException(status_code=404, detail="Google speech is not available")

    connection_manager: "ConnectionService" = request.app.state.app_manager
    text = payload.text
    lang = payload.lang or "en"
    status = audio_manager.text_to_speech(text, lang) or False
    data = {"text": text, "lang": lang, "status": status}
    await connection_manager.broadcast_json(
        {"type": "info", "payload": "Speaking " + text}
    )
    return data


@router.post("/api/volume", response_model=VolumeResponse)
async def set_volume(
    request: Request,
    payload: VolumeRequest,
    audio_manager: "AudioService" = Depends(get_audio_manager),
):
    """
    Endpoint to set the volume.

    Args:
    - payload (VolumeRequest): Contains the desired volume level.
    - audio_manager (AudioService): The audio service for managing audio playback.

    Returns:

        `VolumeResponse`: The response object containing the current volume level.

    Raises:
        HTTPException (404): If there is an error while setting the volume.
    """

    connection_manager: "ConnectionService" = request.app.state.app_manager

    volume = payload.volume
    int_volume = int(volume)

    try:
        await asyncio.to_thread(audio_manager.set_volume, int_volume)
        new_volume = await asyncio.to_thread(audio_manager.get_volume)
        result = {"volume": new_volume}
        await connection_manager.broadcast_json(
            {"type": "volume", "payload": new_volume}
        )
        return result
    except Exception as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.get(
    "/api/volume",
    response_model=VolumeResponse,
    summary="Retrieve the current volume level",
)
async def get_volume(
    audio_manager: "AudioService" = Depends(get_audio_manager),
):
    """
    Retrieve the current volume level.

    Args:
    - audio_manager (AudioService): The audio service for managing audio playback.

    Returns:
        `VolumeResponse`: The response object containing the current volume level.

    Raises:
        HTTPException (404): If there is an error while retrieving the volume level.
    """
    try:
        return {"volume": audio_manager.get_volume()}
    except Exception as err:
        raise HTTPException(status_code=404, detail=str(err))
