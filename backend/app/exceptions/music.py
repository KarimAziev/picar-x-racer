class MusicPlayerError(Exception):
    """Exception raised for errors in the music player."""

    pass


class ActiveMusicTrackRemovalError(Exception):
    """Exception raised when an attempt is made to remove the currently playing music track."""

    pass
