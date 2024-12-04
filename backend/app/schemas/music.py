from enum import Enum
from typing import List, Union

from app.schemas.audio import VolumeData
from pydantic import BaseModel


class MusicDetail(BaseModel):
    """
    A model to represent the details of a music track.

    Attributes:
    - `track` (str): The name of the track.
    - `duration` (float): The duration of the track in seconds.
    """

    track: str
    duration: float


class MusicDetailItem(MusicDetail):
    """
    A model to represent the details of a music track including its removability.

    Attributes:
    - `removable` (bool): Indicator if the music track can be removed.
    """

    removable: bool


class MusicResponse(VolumeData):
    """
    A model to represent the response containing available music tracks and volume levels.

    Attributes:
    - `files` (List[MusicDetailItem]): A list of available music tracks with details.
    - `volume` (str | Any): The system volume level.
    """

    files: List[MusicDetailItem]


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
    - `position` (Union[float, int]): The playback position, in seconds, to set for the current track.
    """

    position: Union[float, int]


class MusicModePayload(BaseModel):
    """
    A model to represent payload information for setting the player's playback mode.

    Attributes:
    - `mode` (MusicPlayerMode): The desired playback mode for the music player.
    """

    mode: MusicPlayerMode


class MusicTrackPayload(BaseModel):
    """
    A model to represent payload information for selecting or interacting with a specific music track.

    Attributes:
    - `track` (str): The identifier or name of the specific track being targeted.
    """

    track: str
