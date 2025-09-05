class MusicPlayerError(Exception):
    """Exception raised for errors in the music player."""

    pass


class ActiveMusicTrackRemovalError(Exception):
    """Exception raised when an attempt is made to remove the currently playing music track."""

    pass


class MusicInitError(Exception):
    """Exception raised for initializing the mixer module for sound loading and playback."""

    pass
