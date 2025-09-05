"""
Endpoints related to music playing.
"""

import asyncio
from typing import TYPE_CHECKING, Annotated, List

from app.api import deps
from app.core.logger import Logger
from app.exceptions.audio import AmixerNotInstalled, AudioVolumeError
from app.exceptions.music import MusicInitError, MusicPlayerError
from app.schemas.common import Message
from app.schemas.music import (
    MusicModePayload,
    MusicPlayerState,
    MusicPositionPayload,
    MusicResponse,
    MusicTrackPayload,
)
from app.services.media.music_file_service import MusicFileService
from fastapi import APIRouter, Depends, HTTPException, Request

if TYPE_CHECKING:
    from app.services.connection_service import ConnectionService
    from app.services.media.audio_service import AudioService
    from app.services.media.music_service import MusicService

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
    music_player: Annotated["MusicService", Depends(deps.get_music_service)],
):
    """
    Toggle play or pause of the current track.

    Also notifies connected clients by broadcasting the updated state over WebSocket.
    """
    try:
        await asyncio.to_thread(music_player.toggle_playing)
        await music_player.broadcast_state()
        return music_player.current_state
    except MusicInitError as err:
        logger.error(f"Failed to init the module mixer: {err}")
        raise HTTPException(status_code=500, detail=str(err))
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
    music_player: Annotated["MusicService", Depends(deps.get_music_service)],
):
    """
    Play a specified music track.

    Broadcasts the updated state to connected clients.
    """

    try:
        await asyncio.to_thread(music_player.play_track, payload.track)
        await music_player.broadcast_state()
        return music_player.current_state
    except MusicInitError as err:
        logger.error(f"Failed to initialize the module mixer: {err}")
        raise HTTPException(status_code=500, detail=str(err))
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
    music_player: Annotated["MusicService", Depends(deps.get_music_service)],
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
    except MusicInitError as err:
        logger.error(f"Failed to initialize the module mixer: {err}")
        raise HTTPException(status_code=500, detail=str(err))
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
    music_player: Annotated["MusicService", Depends(deps.get_music_service)],
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
    except MusicInitError as err:
        logger.error(f"Failed to initialize the module mixer: {err}")
        raise HTTPException(status_code=500, detail=str(err))
    except MusicPlayerError as err:
        logger.error("Failed to update the playback position: %s", err)
        raise HTTPException(status_code=400, detail=str(err))
    except Exception:
        logger.error(
            "Unexpected error occurred while seeking the playback position",
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
    music_player: Annotated["MusicService", Depends(deps.get_music_service)],
):
    """
    Endpoint to update the playback mode of the music player.

    Updates the current playback mode and broadcasts the updated state to connected clients.
    """
    try:
        await asyncio.to_thread(music_player.update_mode, payload.mode)
        await music_player.broadcast_state()
        return music_player.current_state
    except MusicInitError as err:
        logger.error(f"Failed to initialize the module mixer: {err}")
        raise HTTPException(status_code=500, detail=str(err))
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
    music_player: Annotated["MusicService", Depends(deps.get_music_service)],
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
    except MusicInitError as err:
        logger.error(f"Failed to initialize the module mixer: {err}")
        raise HTTPException(status_code=500, detail=str(err))
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
    music_player: Annotated["MusicService", Depends(deps.get_music_service)],
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
    except MusicInitError as err:
        logger.error(f"Failed to initialize the module mixer: {err}")
        raise HTTPException(status_code=500, detail=str(err))
    except MusicPlayerError as err:
        logger.error("Failed to switch the track: %s", err)
        raise HTTPException(status_code=400, detail=str(err))
    except Exception:
        logger.error("Unexpected error while switching the track.", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to switch the track.")


@router.post(
    "/music/order",
    response_model=Message,
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
    music_player: Annotated["MusicService", Depends(deps.get_music_service)],
    music_file_service: Annotated[
        "MusicFileService", Depends(deps.get_music_file_service)
    ],
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
        sorted_tracks = await asyncio.to_thread(
            music_file_service.save_custom_music_order, order
        )
        await music_player.broadcast_state()
        await connection_manager.broadcast_json(
            {"type": "music", "payload": [item.model_dump() for item in sorted_tracks]}
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
    file_manager: Annotated["MusicFileService", Depends(deps.get_music_file_service)],
    audio_manager: Annotated["AudioService", Depends(deps.get_audio_service)],
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
        files = file_manager.list_sorted_tracks()
        return {
            "files": files,
            "volume": music_volume,
        }
    except Exception:
        logger.error("Unexpected error while retrieving music files.", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve music files.")
