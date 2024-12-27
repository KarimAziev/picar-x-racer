import asyncio
from typing import TYPE_CHECKING, List

from app.api.deps import get_audio_manager, get_file_manager, get_music_manager
from app.exceptions.music import MusicPlayerError
from app.schemas.music import (
    MusicModePayload,
    MusicPlayerState,
    MusicPositionPayload,
    MusicResponse,
    MusicTrackPayload,
)
from app.util.logger import Logger
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.services.audio_service import AudioService
    from app.services.connection_service import ConnectionService
    from app.services.file_service import FileService
    from app.services.music_service import MusicService

router = APIRouter()
logger = Logger(__name__)


@router.post(
    "/music/toggle-play",
    summary="Toggle playing of the current track.",
)
async def toggle_play_music(
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Endpoint to toggle play or pause of the current track.

    Args:
    -------------
    - music_player (MusicService): The `MusicService` instance, injected via dependency.

    Behavior:
    -------------
    This endpoint toggles the playback state (play/pause) of the current track
    and notifies connected clients by broadcasting the updated state over WebSocket.

    Returns:
    -------------
    None: The endpoint does not return any data to the caller.
    All connected clients are notified asynchronously via WebSocket.

    Raises:
    -------------
    - HTTPException (400): If there is a `MusicPlayerError`.
    - HTTPException (500): If an unexpected error occurs.
    """
    try:
        await asyncio.to_thread(music_player.toggle_playing)
        await music_player.broadcast_state()
    except MusicPlayerError as err:
        logger.error(f"MusicPlayerError: {err}")
        raise HTTPException(status_code=400, detail=f"Music player issue: {str(err)}")
    except Exception as err:
        logger.error(f"UnexpectedError: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}")


@router.post(
    "/music/track",
    summary="Play a track.",
)
async def play_track(
    payload: MusicTrackPayload,
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Endpoint to play a specified music track.

    Args:
    -------------
    - payload (`MusicTrackPayload`): Contains the name of the track to play.
    - music_player (`MusicService`): The `MusicService` instance, injected via dependency.

    Behavior:
    -------------
    Broadcasts the updated state to connected clients.

    Returns:
    -------------
    None: If successful, no additional payload is returned.
    All connected clients are notified asynchronously via WebSocket.

    Raises:
    -------------
        - HTTPException (400): If there is a `MusicPlayerError`.
        - HTTPException (500): If an unexpected error occurs.
    """
    try:
        await asyncio.to_thread(music_player.play_track, payload.track)
        await music_player.broadcast_state()
    except MusicPlayerError as err:
        logger.error(f"MusicPlayerError: {err}")
        raise HTTPException(status_code=400, detail=f"Music player issue: {str(err)}")
    except Exception as err:
        logger.error(f"UnexpectedError: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}")


@router.post(
    "/music/stop",
    summary="Stop playing of the current track.",
)
async def stop_playing(
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Endpoint to stop playback of the current track.

    Args:
    -------------
    - music_player (MusicService): The `MusicService` instance, injected via dependency.

    Behavior:
    -------------
    Broadcasts the updated state to connected clients.

    Returns:
    -------------
    None: If successful, no additional payload is returned.
    All connected clients are notified asynchronously via WebSocket.

    Raises:
    -------------
    - HTTPException (400): If there is a `MusicPlayerError`.
    - HTTPException (500): If an unexpected error occurs.
    """
    try:
        await asyncio.to_thread(music_player.stop_playing)
        await music_player.broadcast_state()
    except MusicPlayerError as err:
        logger.error(f"MusicPlayerError: {err}")
        raise HTTPException(status_code=400, detail=f"Music player issue: {str(err)}")
    except Exception as err:
        logger.error(f"UnexpectedError: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}")


@router.post("/music/position", response_model=MusicPlayerState)
async def update_position(
    payload: MusicPositionPayload,
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Endpoint to update the playback position of the current track.

    Args:
    -------------
    - payload (MusicPositionPayload): Contains the new playback position in seconds.
    - music_player (MusicService): The `MusicService` instance, injected via dependency.

    Behavior:
    -------------
    Updates the position of the currently playing track and seeks to the specified position (if applicable).
    Broadcasts the state to connected clients.


    Returns:
    --------------
    MusicPlayerState: Details such as the currently playing track, playback
    position, playback mode, and whether or not music is playing.
    Also, all connected clients are notified asynchronously via WebSocket.

    Raises:
    - HTTPException (400): If there is a `MusicPlayerError`.
    - HTTPException (500): If an unexpected error occurs.
    """
    next_pos = float(payload.position)
    logger.info(f"seeking track %s", next_pos)
    try:
        await asyncio.to_thread(music_player.update_position, next_pos)
        await music_player.broadcast_state()
        return music_player.current_state
    except MusicPlayerError as err:
        logger.error(f"MusicPlayerError: {err}")
        raise HTTPException(status_code=400, detail=f"Music player issue: {str(err)}")
    except Exception as err:
        logger.error(f"UnexpectedError: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}")


@router.post("/music/mode")
async def update_mode(
    payload: MusicModePayload,
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Endpoint to update the playback mode of the music player.

    Args:
    -------------

     - payload (MusicModePayload): Contains the new playback mode.
     - music_player (MusicService): The `MusicService` instance, injected via dependency.

    Behavior:
    -------------
    Updates the current playback mode (e.g., LOOP, SINGLE) and broadcasts the updated state to connected clients.

    Returns:
    --------------
    None: If successful, no additional payload is returned.
    All connected clients are notified asynchronously via WebSocket.

    Raises:
    - HTTPException (400): If there is a `MusicPlayerError`.
    - HTTPException (500): If an unexpected error occurs.
    """
    try:
        await asyncio.to_thread(music_player.update_mode, payload.mode)
        await music_player.broadcast_state()
    except MusicPlayerError as err:
        logger.error(f"MusicPlayerError: {err}")
        raise HTTPException(status_code=400, detail=f"Music player issue: {str(err)}")
    except Exception as err:
        logger.error(f"UnexpectedError: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}")


@router.post("/music/next-track")
async def next_track(
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Endpoint to switch to the next track in the playlist.

    Args:
    --------------
    - music_player (MusicService): The `MusicService` instance, injected via dependency.

    Behavior:
    -------------
    Advances playback to the next track in the playlist. In loop modes, the playlist wraps around when the last track is reached.
    Broadcasts the updated state to connected clients.

    Returns:
    --------------
    None: If successful, no additional payload is returned.
    All connected clients are notified asynchronously via WebSocket.

    Raises:
    - HTTPException (400): If there is a `MusicPlayerError`.
    - HTTPException (500): If an unexpected error occurs.
    """
    try:
        await asyncio.to_thread(music_player.next_track)
        await music_player.broadcast_state()
    except MusicPlayerError as err:
        logger.error(f"MusicPlayerError: {err}")
        raise HTTPException(status_code=400, detail=f"Music player issue: {str(err)}")
    except Exception as err:
        logger.error(f"UnexpectedError: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}")


@router.post("/music/prev-track")
async def prev_track(
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Endpoint to switch to the previous track in the playlist.

    Args:
    --------------
    - music_player (MusicService): The `MusicService` instance, injected via dependency.

    Behavior:
    -------------
    Moves playback to the previous track in the playlist.
    In loop modes, the playlist wraps around when the first track is reached.
    Broadcasts the updated state to connected clients.

    Returns:
    --------------
    None: If successful, no additional payload is returned.
    All connected clients are notified asynchronously via WebSocket.

    Raises:
    --------------
    - HTTPException (400): If there is a `MusicPlayerError`.
    - HTTPException (500): If an unexpected error occurs.
    """
    try:
        await asyncio.to_thread(music_player.prev_track)
        await music_player.broadcast_state()
    except MusicPlayerError as err:
        logger.error(f"MusicPlayerError: {err}")
        raise HTTPException(status_code=400, detail=f"Music player issue: {str(err)}")
    except Exception as err:
        logger.error(f"UnexpectedError: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}")


@router.post("/music/order")
async def save_music_order(
    request: Request,
    order: List[str],
    music_player: "MusicService" = Depends(get_music_manager),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Endpoint to save the custom order of music tracks in the playlist.

    Args:
    -------------
    - request (Request): The HTTP request object (for accessing application state).
    - order (List[str]): The new custom order list for tracks.
    - music_player (MusicService): The `MusicService` instance, injected via dependency.
    - file_manager (FileService): The `FileService` instance, injected via dependency.

    Behavior:
    -------------
    Updates the order of tracks in the playlist and saves this new order using the FileService.
    Notifies connected clients about the new playlist order.

    Returns:
    -------------
    dict: A message confirming the successful update of the music order.

    Raises:
    -------------
    - HTTPException (400): If any error occurs while updating the track order.
    """
    logger.info("Music order update %s", order)
    connection_manager: "ConnectionService" = request.app.state.app_manager
    try:
        await asyncio.to_thread(music_player.update_tracks, order)
        await music_player.broadcast_state()
        files = await asyncio.to_thread(file_manager.list_all_music_with_details)
        settings = await asyncio.to_thread(file_manager.load_settings)
        await connection_manager.broadcast_json({"type": "music", "payload": files})
        await connection_manager.broadcast_json(
            {"type": "settings", "payload": {"music": settings.get("music")}}
        )
        return {"message": "Custom music order saved successfully!"}
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@router.get("/music", response_model=MusicResponse)
async def get_music_tracks(
    file_manager: "FileService" = Depends(get_file_manager),
    audio_manager: "AudioService" = Depends(get_audio_manager),
):
    """
    Retrieve the list of available music tracks.

    Args:
    --------------
    - file_manager (FileService): The file service for managing files.
    - audio_manager (AudioService): The audio service for managing audio playback.

    Returns:
    --------------
    `MusicResponse`: The response object containing the list of available music tracks, system volume, and music volume.

    Raises:
    --------------
    - HTTPException (404): If there is an error while retrieving the music tracks.
    """
    music_volume = await asyncio.to_thread(audio_manager.get_volume)
    try:
        files = file_manager.list_all_music_with_details()
        return {
            "files": files,
            "volume": music_volume,
        }
    except Exception as err:
        raise HTTPException(status_code=404, detail=str(err))
