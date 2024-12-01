import asyncio
from os import path
from typing import TYPE_CHECKING, List

from app.api.deps import get_audio_manager, get_file_manager
from app.schemas.audio import (
    MusicResponse,
    PlayMusicItem,
    PlayMusicResponse,
    PlaySoundItem,
    PlaySoundResponse,
    PlayStatusResponse,
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


@router.get(
    "/api/play-status",
    response_model=PlayStatusResponse,
    summary="Get the current play status of the music",
)
async def get_play_status(
    file_manager: "FilesService" = Depends(get_file_manager),
    audio_manager: "AudioService" = Depends(get_audio_manager),
):
    """
    Retrieve the current play status of the music.

    Args:

    - file_manager (FilesService): The file service for managing files.
    - audio_manager (AudioService): The audio service for managing audio playback.

    Returns:
        `PlayStatusResponse`: The current play status including track and duration details.
    """
    result = audio_manager.get_music_play_status()

    if result is None:
        settings = file_manager.load_settings()
        track = settings.get("default_music")
        dir = file_manager.get_music_directory(track)
        file = path.join(dir, track)
        base_dict = {"playing": False}
        details = file_manager.get_audio_file_details_cached(file)
        if isinstance(details, dict):
            return {**base_dict, **details}
    else:
        return result


@router.post(
    "/api/play-music", response_model=PlayMusicResponse, summary="Play audio track"
)
async def play_music(
    payload: PlayMusicItem,
    file_manager: "FilesService" = Depends(get_file_manager),
    audio_manager: "AudioService" = Depends(get_audio_manager),
):
    """
    Endpoint to play music.

    Args:
    - payload (PlayMusicItem): Contains the track details for the music to be played.
    - file_manager (FilesService): The file service for managing files.
    - audio_manager (AudioService): The audio service for managing audio playback.

    Returns:
        PlayMusicResponse: The response object containing the play music result.

    Raises:
        HTTPException (500): If there is an error while playing the music.
    """
    filename = payload.track
    force = payload.force
    start = payload.start or 0.0
    logger.info(f"Request to play music {filename}")
    if filename is None:
        result = audio_manager.stop_music()
        return {"playing": audio_manager.is_music_playing()}

    try:
        dir = file_manager.get_music_directory(filename)
        file = path.join(dir, filename)
        logger.debug(f"Playing music {file}")
        result = audio_manager.play_music(track_path=file, force=force, start=start)
        return result
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


@router.get("/api/music", response_model=MusicResponse)
async def get_music_tracks(
    file_manager: "FilesService" = Depends(get_file_manager),
    audio_manager: "AudioService" = Depends(get_audio_manager),
):
    """
    Retrieve the list of available music tracks.

    Args:
    - file_manager (FilesService): The file service for managing files.
    - audio_manager (AudioService): The audio service for managing audio playback.

    Returns:
        `MusicResponse`: The response object containing the list of available music tracks, system volume, and music volume.

    Raises:
        HTTPException (404): If there is an error while retrieving the music tracks.
    """
    amixer_volume = audio_manager.get_amixer_volume()
    music_volume = audio_manager.get_volume()
    try:
        files = file_manager.list_all_music_with_details()
        return {
            "files": files,
            "system_volume": amixer_volume,
            "volume": music_volume,
        }
    except Exception as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.post("/api/music/order")
async def save_music_order(
    request: Request,
    order: List[str],
    file_manager: "FilesService" = Depends(get_file_manager),
):
    """
    Save the custom order of music tracks.

    Args:
    - order (List[str]): List of music file names in the desired order.

    Returns:
        dict: Confirmation message.

    Raises:
        HTTPException (400): If the order is invalid.
    """
    connection_manager: "ConnectionService" = request.app.state.app_manager
    try:
        await asyncio.to_thread(file_manager.save_custom_music_order, order)
        files = await asyncio.to_thread(file_manager.list_all_music_with_details)
        await connection_manager.broadcast_json({"type": "music", "payload": files})
        await connection_manager.broadcast_json(
            {"type": "settings", "payload": {"music_order": order}}
        )
        return {"message": "Custom music order saved successfully!"}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))
