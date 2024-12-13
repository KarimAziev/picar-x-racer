from enum import Enum
from typing import List, Optional, Union

from app.schemas.audio import VolumeData
from pydantic import BaseModel, Field


class MusicDetail(BaseModel):
    """
    A model to represent the details of a music track.

    Attributes:
    - `track` (str): The name of the track.
    - `duration` (float): The duration of the track in seconds.
    """

    track: str = Field(
        ...,
        min_length=1,
        description="The name of the track.",
        examples=["my-song.mp3"],
    )
    duration: float = Field(
        ...,
        gt=0,
        description="The duration of the track in seconds. Must be greater than 0.",
        examples=[149.722],
    )


class MusicDetailItem(MusicDetail):
    """
    A model to represent the details of a music track including its removability.
    """

    removable: bool = Field(
        ..., description="Indicates whether the music track can be removed."
    )


class MusicResponse(VolumeData):
    """
    A model to represent the response containing available music tracks and volume levels.
    """

    files: List[MusicDetailItem] = Field(
        ..., description="A list of available music tracks with detailed information."
    )


class MusicPlayerMode(str, Enum):
    """
    An enumeration to represent the playback modes for the music player.

    Enum Values:
    - `LOOP` (str): Repeat all tracks (auto-loop playlist).
    - `QUEUE` (str): Play tracks in order without repeating (one loop through the playlist).
    - `SINGLE` (str): Play a single track once and then stop.
    - `LOOP_ONE` (str): Repeat a single track continuously.
    """

    LOOP = "loop"  # Repeat all tracks (auto-loop playlist)
    QUEUE = "queue"  # Play in order without repeating (one loop through the playlist)
    SINGLE = "single"  # Play a single track once, then stop
    LOOP_ONE = "loop_one"  # Repeat a single track continuously


class MusicPositionPayload(BaseModel):
    """
    A model to represent payload information for updating the playback position.

    Attributes:
    - `position`: The playback position, in seconds, to set for the current track.
    """

    position: Union[float, int] = Field(
        ...,
        ge=0,
        description="The playback position, in seconds, to set for the current track",
    )


class MusicModePayload(BaseModel):
    """
    A model to represent payload information for setting the player's playback mode.

    Attributes:
    - `mode`: The desired playback mode for the music player.
    """

    mode: MusicPlayerMode = Field(
        ..., description="The desired playback mode for the music player."
    )


class MusicTrackPayload(BaseModel):
    """
    A model to represent payload information for selecting or interacting with a specific music track.

    Attributes:
    - `track`: The name of the specific track being targeted.
    """

    track: str = Field(
        ...,
        min_length=1,
        description="The name of the track.",
        examples=["my-song.mp3"],
    )


class MusicPlayerState(BaseModel):
    """
    A model to represent the music player state.

    Attributes:
    - `track`: The name of the current track.
    - `position`: The position in seconds of the current track.
    - `is_playing`: A boolean indicating whether the track is currently playing.
    - `duration`: The duration in seconds of the current track.
    - `mode`: The playback mode for the music player.
    """

    track: Optional[str] = Field(
        None, description="The name of the current track.", examples=["my-song.mp3"]
    )
    position: int = Field(
        ...,
        ge=0,
        description="The position in seconds of the current track.",
        examples=[30],
    )
    is_playing: bool = Field(
        ..., description="A boolean indicating whether the track is currently playing."
    )
    duration: Union[float, int] = Field(
        ...,
        ge=0,
        description="The duration in seconds of the current track.",
        examples=[149.722],
    )
    mode: MusicPlayerMode = Field(
        ..., description="The playback mode for the music player."
    )


class MusicOrder(BaseModel):
    order: Optional[List[str]] = Field(
        ...,
        description="The order of tracks",
        examples=[["my-song.wav", "Extreme_Epic_Cinematic_Action_-_StudioKolomna.mp3"]],
    )


class MusicSettings(MusicOrder):
    mode: Optional[MusicPlayerMode] = None
