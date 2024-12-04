class AudioVolumeError(Exception):
    """Exception raised for errors related to audio volume operations."""

    pass


class AmixerNotInstalled(Exception):
    """Exception raised when amixer is not installed on the system."""

    pass
