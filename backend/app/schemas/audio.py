from typing import Any, List, Optional

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


class PlayStatusResponse(BaseModel):
    """
    A model to represent the current play status of the music.

    Attributes:
    - `playing` (bool): Indicator if the music is currently playing.
    - `track` (str): The name of the playing track.
    - `duration` (Optional[float]): The duration of the track in seconds. Defaults to None.
    - `start` (Optional[float]): The start time of the track in seconds. Defaults to None.
    """

    playing: bool
    track: str
    duration: Optional[float] = None
    start: Optional[float] = None


class PlayMusicResponse(BaseModel):
    """
    A model to represent the response after playing a music track.

    Attributes:
    - `playing` (bool): Indicator if the music is currently playing.
    - `track` (Optional[str]): The name of the playing track. Defaults to None.
    - `start` (Optional[float]): The start time of the track in seconds. Defaults to None.
    """

    playing: bool
    track: Optional[str] = None
    start: Optional[float] = None


class PlayMusicItem(BaseModel):
    """
    A model to represent the details required to play a music track.

    Attributes:
    - `force` (bool): Indicator if the track should be forcefully played.
    - `track` (Optional[str]): The name of the track to play. Defaults to None.
    - `start` (Optional[float]): The start time of the track in seconds. Defaults to None.
    """

    force: bool
    track: Optional[str] = None
    start: Optional[float] = None


class PlaySoundItem(BaseModel):
    """
    A model to represent the details required to play a sound track.

    Attributes:
    - `track` (str): The name of the track to play.
    - `force` (Optional[bool]): Indicator if the track should be forcefully played. Defaults to None.
    """

    track: str
    force: Optional[bool] = None


class PlaySoundResponse(PlayStatusResponse):
    """
    A model to represent the response after playing a sound track. Inherits from PlayStatusResponse.
    """

    pass


class PlayTTSItem(BaseModel):
    """
    A model to represent the details required to convert text to speech.

    Attributes:
    - `text` (str): The text to convert to speech.
    - `lang` (Optional[str]): The language of the text. Defaults to None.
    """

    text: str
    lang: Optional[str] = None


class PlayTTSResponse(BaseModel):
    """
    A model to represent the response after converting text to speech.

    Attributes:
    - `text` (str): The text that was converted to speech.
    - `lang` (str): The language of the text.
    """

    text: str
    lang: str


class VolumeRequest(BaseModel):
    """
    A model to represent the volume adjustment request.

    Attributes:
    - `volume` (int | float): The desired volume level.
    """

    volume: int | float


class VolumeResponse(BaseModel):
    """
    A model to represent the current volume level response.

    Attributes:
    - `volume` (float): The current volume level.
    """

    volume: float


class MusicResponse(VolumeResponse):
    """
    A model to represent the response containing available music tracks and volume levels. Inherits from VolumeResponse.

    Attributes:
    - `files` (List[MusicDetailItem]): A list of available music tracks with details.
    - `system_volume` (str | Any): The system volume level.
    """

    files: List[MusicDetailItem]
    system_volume: str | Any
