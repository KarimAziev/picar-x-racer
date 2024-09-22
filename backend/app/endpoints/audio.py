from os import path
from typing import TYPE_CHECKING, Any, Dict

from app.deps import get_audio_manager, get_file_manager
from app.util.logger import Logger
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from app.controllers.audio_controller import AudioController
    from app.controllers.files_controller import FilesController

router = APIRouter()
logger = Logger(__name__)


@router.post("/api/play-sound")
async def play_sound(
    payload: Dict[str, Any],
    file_manager: "FilesController" = Depends(get_file_manager),
    audio_manager: "AudioController" = Depends(get_audio_manager),
):
    filename = payload.get("filename")

    force = payload.get("force", False)
    if not isinstance(filename, str):
        raise HTTPException(status_code=400, detail="Invalid settings format")

    logger.info(f"Request to play sound {filename}")
    try:
        dir = file_manager.get_sound_directory(filename)
        file = path.join(dir, filename)
        result = audio_manager.play_sound(file, force)
        return JSONResponse(content=result)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.get("/api/play-status")
async def get_play_status(
    file_manager: "FilesController" = Depends(get_file_manager),
    audio_manager: "AudioController" = Depends(get_audio_manager),
):
    result = audio_manager.get_music_play_status()

    if result is None:
        default_track = file_manager.load_settings()
        track = default_track.get("default_music")
        dir = file_manager.get_music_directory(track)
        file = path.join(dir, track)
        duration = audio_manager.music.music_get_duration(file)
        return JSONResponse(
            content={"playing": False, "track": track, "duration": duration}
        )
    else:
        return JSONResponse(content=result)


@router.post("/api/play-music")
async def play_music(
    payload: Dict[str, Any],
    file_manager: "FilesController" = Depends(get_file_manager),
    audio_manager: "AudioController" = Depends(get_audio_manager),
):
    filename = payload.get("filename")
    force = payload.get("force", False)
    start = payload.get("start", 0.0)
    logger.info(f"request to play music {filename}")
    if filename is None:
        result = audio_manager.stop_music()
        return JSONResponse(content={"playing": audio_manager.is_music_playing()})

    try:
        dir = file_manager.get_music_directory(filename)
        file = path.join(dir, filename)
        logger.debug(f"playing {file}")
        result = audio_manager.play_music(track_path=file, force=force, start=start)
        return JSONResponse(content=result)
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))


@router.post("/api/play-tts")
async def text_to_speech(
    payload: Dict[str, str],
    file_manager: "FilesController" = Depends(get_file_manager),
    audio_manager: "AudioController" = Depends(get_audio_manager),
):
    if not audio_manager.google_speech_available:
        raise HTTPException(status_code=404, detail="Google speech is not available")

    if not payload.get("text"):
        settings = file_manager.load_settings()
        text = settings.get("default_text")
        lang = settings.get("default_language", "en")
    else:
        text = payload.get("text")
        lang = payload.get("lang", "en")

    if text and lang:
        audio_manager.text_to_speech(text, lang)
        return JSONResponse(content={"status": True})
    else:
        raise HTTPException(status_code=400, detail="Invalid settings format")


@router.post("/api/volume")
async def set_volume(
    payload: Dict[str, int],
    audio_manager: "AudioController" = Depends(get_audio_manager),
):
    if not isinstance(payload, Dict) or "volume" not in payload:
        raise HTTPException(status_code=400, detail="Invalid format")

    volume = payload["volume"]

    try:
        audio_manager.set_volume(volume)
        return JSONResponse(content={"volume": audio_manager.get_volume()})
    except Exception as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.get("/api/volume")
async def get_volume(
    audio_manager: "AudioController" = Depends(get_audio_manager),
):
    try:
        return JSONResponse(content={"volume": audio_manager.get_volume()})
    except Exception as err:
        raise HTTPException(status_code=404, detail=str(err))


@router.get("/api/music")
async def get_music_tracks(
    file_manager: "FilesController" = Depends(get_file_manager),
    audio_manager: "AudioController" = Depends(get_audio_manager),
):
    amixer_volume = audio_manager.get_amixer_volume()
    music_volume = audio_manager.get_volume()
    try:
        files = file_manager.list_all_music_with_details()
        return JSONResponse(
            content={
                "files": files,
                "system_volume": amixer_volume,
                "volume": music_volume,
            }
        )
    except Exception as err:
        raise HTTPException(status_code=404, detail=str(err))
