from app.exceptions.audio import AudioVolumeUnsupported, AudioVolumeUnavailable


class UnavailableVolumeController:
    """Volume controller that reports an unavailable platform capability."""

    error_type = AudioVolumeUnavailable

    def __init__(self, reason: str) -> None:
        self._reason = reason

    def get_volume(self) -> int:
        raise self.error_type(self._reason)

    def set_volume(self, volume: int) -> None:
        raise self.error_type(self._reason)


class UnsupportedVolumeController(UnavailableVolumeController):
    """Volume controller for platforms without a supported implementation."""

    error_type = AudioVolumeUnsupported
