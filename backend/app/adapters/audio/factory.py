import platform
import shutil
from typing import Callable, Optional

from app.adapters.audio.alsa_volume_controller import AlsaVolumeController
from app.adapters.audio.macos_volume_controller import MacOSVolumeController
from app.adapters.audio.unsupported_volume_controller import (
    UnavailableVolumeController,
    UnsupportedVolumeController,
)
from app.services.media.volume_controller import VolumeController


def create_volume_controller(
    system_name: Optional[str] = None,
    command_lookup: Callable[[str], Optional[str]] = shutil.which,
) -> VolumeController:
    """Create the best system volume controller for the current platform."""
    current_system = system_name or platform.system()

    if current_system == "Darwin":
        if command_lookup("osascript") is not None:
            return MacOSVolumeController()
        return UnavailableVolumeController(
            "macOS volume control is unavailable because 'osascript' was not found."
        )

    if current_system == "Linux":
        if command_lookup("amixer") is not None:
            return AlsaVolumeController()
        return UnavailableVolumeController(
            "Linux volume control is unavailable because 'amixer' was not found."
        )

    return UnsupportedVolumeController(
        f"System volume control is not supported on {current_system}."
    )
