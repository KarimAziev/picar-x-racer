"""
Endpoints related to music playing.
"""

import asyncio
from typing import TYPE_CHECKING, List

from app.api.deps import get_audio_manager, get_file_manager, get_music_manager
from app.core.logger import Logger
from app.exceptions.audio import AmixerNotInstalled, AudioVolumeError
from app.exceptions.music import MusicPlayerError
from app.schemas.music import (
    MusicModePayload,
    MusicPlayerState,
    MusicPositionPayload,
    MusicResponse,
    MusicTrackPayload,
)
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
    response_model=MusicPlayerState,
    response_description="Details such as the currently playing track, "
    "playback position, playback mode, and whether or not music is playing.",
    responses={
        400: {
            "description": "Bad Request. There are no music track to play or stop.",
            "content": {"application/json": {"example": {"detail": "No music track."}}},
        },
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to toggle music playing."}
                }
            },
        },
    },
)
async def toggle_play_music(
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Toggle play or pause of the current track.

    Also notifies connected clients by broadcasting the updated state over WebSocket.
    """
    try:
        await asyncio.to_thread(music_player.toggle_playing)
        await music_player.broadcast_state()
        return music_player.current_state
    except MusicPlayerError as err:
        logger.error(f"Failed to toggle music playing: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        logger.error(
            "Unexpected error occurred while toggling music playing.", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Failed to toggle music playing.")


@router.post(
    "/music/track",
    summary="Play a music track.",
    response_model=MusicPlayerState,
    response_description="Details such as the currently playing track, "
    "playback position, playback mode, and whether or not music is playing.",
    responses={
        400: {
            "description": "Bad Request. No music track to play.",
            "content": {"application/json": {"example": {"detail": "No music track."}}},
        },
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to play the track 'my_track.wav'."}
                }
            },
        },
        404: {
            "description": "The requested music track is not found.",
            "content": {
                "application/json": {
                    "example": {"detail": "The track 'my_song.mp3' is not found."}
                }
            },
        },
    },
)
async def play_track(
    payload: MusicTrackPayload,
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Play a specified music track.

    Broadcasts the updated state to connected clients.
    """

    try:
        await asyncio.to_thread(music_player.play_track, payload.track)
        await music_player.broadcast_state()
        return music_player.current_state
    except MusicPlayerError as err:
        logger.error(f"Failed to play the track %s: %s", payload.track, err)
        raise HTTPException(status_code=400, detail=str(err))
    except FileNotFoundError:
        logger.error("The music file for '%s' is not found", payload.track)
        raise HTTPException(
            status_code=404, detail=f"The track '{payload.track}' is not found."
        )
    except Exception as err:
        logger.error(
            "Unexpected error while playing the track '%s'.",
            payload.track,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to play the track '{payload.track}'."
        )


@router.post(
    "/music/stop",
    summary="Stop playing of the current track.",
    response_model=MusicPlayerState,
    response_description="Details such as the currently playing track, "
    "playback position, playback mode, and whether or not music is playing.",
    responses={
        400: {
            "description": "Bad Request. There are no music track to play or stop.",
            "content": {"application/json": {"example": {"detail": "No music track."}}},
        },
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {"example": {"detail": "Failed to stop playing."}}
            },
        },
    },
)
async def stop_playing(
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Stop playback of the current track.

    Behavior:
    -------------
    Broadcasts the updated state to connected clients.
    """
    try:
        await asyncio.to_thread(music_player.stop_playing)
        await music_player.broadcast_state()
        return music_player.current_state
    except MusicPlayerError as err:
        logger.error(f"Failed to stop the playing: %s", err)
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        logger.error("Unexpected error while stopping the track.", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to stop playing.")


@router.post(
    "/music/position",
    response_model=MusicPlayerState,
    response_description="Details such as the currently playing track, "
    "playback position, playback mode, and whether or not music is playing.",
    responses={
        400: {
            "description": "Bad Request. There are no music track to play or stop.",
            "content": {"application/json": {"example": {"detail": "No music track."}}},
        },
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to update the position."}
                }
            },
        },
    },
)
async def update_position(
    payload: MusicPositionPayload,
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Update the playback position of the current track.

    Behavior:
    -------------
    Updates the position of the currently playing track.

    Also seeks to the specified position (if applicable).

    Broadcasts the state to connected clients.
    """
    next_pos = float(payload.position)
    logger.info(f"Updating music position to %s", next_pos)
    try:
        await asyncio.to_thread(music_player.update_position, next_pos)
        await music_player.broadcast_state()
        return music_player.current_state
    except MusicPlayerError as err:
        logger.error("Failed to update the playback position: %s", err)
        raise HTTPException(status_code=400, detail=str(err))
    except Exception:
        logger.error(
            "Unexpected error occured while seeking the playback position",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to update the position.")


@router.post(
    "/music/mode",
    response_model=MusicPlayerState,
    response_description="Details such as the currently playing track, "
    "playback position, playback mode, and whether or not music is playing.",
    responses={
        400: {
            "description": "Bad Request. No music track is found.",
            "content": {"application/json": {"example": {"detail": "No music track."}}},
        },
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to update the mode."}
                }
            },
        },
    },
)
async def update_mode(
    payload: MusicModePayload,
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Endpoint to update the playback mode of the music player.

    Updates the current playback mode and broadcasts the updated state to connected clients.
    """
    try:
        await asyncio.to_thread(music_player.update_mode, payload.mode)
        await music_player.broadcast_state()
        return music_player.current_state
    except MusicPlayerError as err:
        logger.error("Failed to update the playback mode: %s", err)
        raise HTTPException(status_code=400, detail=str(err))
    except Exception:
        logger.error("Unexpected error while updating the mode.", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update the mode.")


@router.post(
    "/music/next-track",
    response_model=MusicPlayerState,
    response_description="Details such as the currently playing track, "
    "playback position, playback mode, and whether or not music is playing.",
    responses={
        400: {
            "description": "Bad Request. No music track is found.",
            "content": {"application/json": {"example": {"detail": "No music track."}}},
        },
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to switch the track."}
                }
            },
        },
    },
)
async def next_track(
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Switch to the next track in the playlist.

    Behavior:
    -------------
    Advances playback to the next track in the playlist.

    In loop modes, the playlist wraps around when the last track is reached.

    Broadcasts the updated state to connected clients.
    """
    try:
        await asyncio.to_thread(music_player.next_track)
        await music_player.broadcast_state()
        return music_player.current_state
    except MusicPlayerError as err:
        logger.error("Failed to switch the track: %s", err)
        raise HTTPException(status_code=400, detail=str(err))
    except Exception:
        logger.error("Unexpected error while switching the track.", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to switch the track.")


@router.post(
    "/music/prev-track",
    response_model=MusicPlayerState,
    response_description="Details such as the currently playing track, "
    "playback position, playback mode, and whether or not music is playing.",
    responses={
        400: {
            "description": "Bad Request. No music track is found.",
            "content": {"application/json": {"example": {"detail": "No music track."}}},
        },
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to switch the track."}
                }
            },
        },
    },
)
async def prev_track(
    music_player: "MusicService" = Depends(get_music_manager),
):
    """
    Endpoint to switch to the previous track in the playlist.

    Behavior:
    -------------
    Moves playback to the previous track in the playlist.

    In loop modes, the playlist wraps around when the first track is reached.

    Broadcasts the updated state to connected clients.
    """
    try:
        await asyncio.to_thread(music_player.prev_track)
        await music_player.broadcast_state()
        return music_player.current_state
    except MusicPlayerError as err:
        logger.error("Failed to switch the track: %s", err)
        raise HTTPException(status_code=400, detail=str(err))
    except Exception:
        logger.error("Unexpected error while switching the track.", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to switch the track.")


@router.post(
    "/music/order",
    responses={
        200: {
            "description": "A message that the new order is saved successfully.",
            "content": {
                "application/json": {
                    "example": {"message": "Music order saved successfully!"}
                }
            },
        },
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to update music order."}
                }
            },
        },
    },
)
async def save_music_order(
    request: Request,
    order: List[str],
    music_player: "MusicService" = Depends(get_music_manager),
    file_manager: "FileService" = Depends(get_file_manager),
):
    """
    Save the custom order of music tracks in the playlist.

    Behavior:
    -------------
    Updates the order of tracks in the playlist and saves this new order.

    Notifies connected clients about the new playlist order.

    Returns:
    -------------
    A message confirming the successful update of the music order.
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
        return {"message": "Music order saved successfully!"}
    except Exception:
        logger.error("Unexpected error while saving the music order", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to update music order.")


@router.get(
    "/music",
    response_model=MusicResponse,
    response_description="A list of available music tracks with detailed information, "
    "such as duration and whether the music track can be removed, etc.",
    responses={
        500: {
            "description": "Internal Server Error: Unexpected error occurred.",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to retrieve music files."}
                }
            },
        },
    },
)
async def get_music_tracks(
    file_manager: "FileService" = Depends(get_file_manager),
    audio_manager: "AudioService" = Depends(get_audio_manager),
):
    """
    Retrieve the list of available music tracks.

    Returns:
    --------------
    The response object containing the list of available music tracks and system volume.
    """
    music_volume = 0
    try:
        music_volume = await asyncio.to_thread(audio_manager.get_volume)
    except (AmixerNotInstalled, AudioVolumeError) as e:
        logger.error("Couldn't retrieve a volume: %s", e)
    except Exception:
        logger.error("Unexpected error while getting the volume level", exc_info=True)
    try:
        files = file_manager.list_all_music_with_details()
        return {
            "files": files,
            "volume": music_volume,
        }
    except Exception:
        logger.error("Unexpected error while retrieving music files.", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve music files.")
