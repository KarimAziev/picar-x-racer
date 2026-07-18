from typing import Union

from app.services.media.audio_metadata_service import AudioMetadataService
from app.services.media.volume_controller import VolumeController


class AudioService:
    """
    Application-facing facade for audio metadata and system volume control.
    """

    def __init__(
        self,
        volume_controller: VolumeController,
        metadata_service: AudioMetadataService,
    ) -> None:
        self._volume_controller = volume_controller
        self._metadata_service = metadata_service

    def get_audio_duration(self, filename: str) -> float:
        """
        Get the duration of an audio file in seconds.
        """
        return self._metadata_service.get_duration(filename)

    def get_volume(self) -> int:
        """
        Retrieve the current playback volume level as a percentage.
        """
        return self._volume_controller.get_volume()

    def set_volume(self, volume_percentage: Union[int, float]) -> None:
        """
        Set the playback volume to the specified level.

        Args:
        --------------
        `volume_percentage`: Target volume (0 to 100).

        """
        normalized_volume = int(max(0, min(100, volume_percentage)))
        self._volume_controller.set_volume(normalized_volume)
