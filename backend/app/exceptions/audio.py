class AudioVolumeError(Exception):
    """Exception raised for errors related to audio volume operations."""

    pass


class AudioVolumeUnavailable(AudioVolumeError):
    """Exception raised when no usable volume backend is available."""

    pass


class AudioVolumeUnsupported(AudioVolumeUnavailable):
    """Exception raised when system volume control is unsupported."""

    pass


class AmixerNotInstalled(AudioVolumeUnavailable):
    """Deprecated compatibility exception for unavailable ALSA volume control."""

    pass
