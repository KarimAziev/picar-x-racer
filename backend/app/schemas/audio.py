from typing import Any, List, Optional

from pydantic import BaseModel


class MusicDetail(BaseModel):
    track: str
    duration: float


class MusicDetailItem(MusicDetail):
    removable: bool


class PlayStatusResponse(BaseModel):
    playing: bool
    track: str
    duration: Optional[float] = None
    start: Optional[float] = None


class PlayMusicResponse(BaseModel):
    playing: bool
    track: Optional[str] = None
    start: Optional[float] = None


class PlayMusicItem(BaseModel):
    force: bool
    track: Optional[str] = None
    start: Optional[float] = None


class PlaySoundItem(BaseModel):
    track: str
    force: Optional[bool] = None


class PlaySoundResponse(PlayStatusResponse):
    pass


class PlayTTSItem(BaseModel):
    text: str
    lang: Optional[str] = None


class PlayTTSResponse(BaseModel):
    text: str
    lang: str


class VolumeRequest(BaseModel):
    volume: int | float


class VolumeResponse(BaseModel):
    volume: float


class MusicResponse(VolumeResponse):
    files: List[MusicDetailItem]
    system_volume: str | Any
