from pydub import AudioSegment


class AudioMetadataService:
    """Reads metadata from audio files."""

    def get_duration(self, filename: str) -> float:
        """Return the duration of an audio file in seconds."""
        audio = AudioSegment.from_file(filename)
        return len(audio) / 1000.0
