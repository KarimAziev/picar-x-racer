from typing import Protocol


class VolumeController(Protocol):
    """Platform-independent system volume control contract."""

    def get_volume(self) -> int:
        """Return the current output volume as a percentage."""
        ...

    def set_volume(self, volume: int) -> None:
        """Set the output volume to a percentage from 0 through 100."""
        ...
