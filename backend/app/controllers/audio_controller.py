import time
from os import path
from typing import Any, Optional

from app.robot_hat.music import Music
from app.util.constrain import constrain
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta

try:
    from google_speech import Speech

    google_speech_available = True
except ImportError:
    google_speech_available = False


class AudioController(metaclass=SingletonMeta):
    """
    The AudioController class provides methods for controlling audio playback,
    including music, sounds, and text-to-speech functionality.

    It ensures that only one instance of the class exists, using the Singleton design pattern.
    """

    def __init__(self):
        """
        Initializes the AudioController instance.

        Attributes:
            music (Music): An instance of the Music class for handling music operations.
            logger (Logger): An instance of the Logger class for logging information.
            google_speech_available (bool): Indicates whether the google_speech module is available.
            sound_playing (bool): A flag indicating if a sound is currently playing.
            sound_end_time (float or None): The time when the currently playing sound will end, or None if no sound is playing.
        """
        self.music = Music()
        self.logger = Logger(__name__)
        self.google_speech_available = google_speech_available
        self.music.music_set_volume(100)
        self.sound_playing = False
        self.sound_end_time = None
        self.last_response: Optional[dict[str, Any]] = None

    def set_volume(self, volume: int):
        """
        Set the music volume.

        Args:
            volume (int): The volume level (0-100).

        Returns:
            None
        """
        self.music.music_set_volume(constrain(volume, 0, 100))

    def get_volume(self):
        """
        Get the current music volume level.

        Returns:
            int: The current volume level (0-100).
        """
        return self.music.music_get_volume()

    def text_to_speech(self, words: str, lang="en"):
        """
        Convert the given text to speech and play it.

        Args:
            words (str): The text to convert to speech.
            lang (str): The language of the text. Default is "en".

        Returns:
            None
        """

        if google_speech_available:
            try:
                self.logger.info(f"text-to-speech: {words} lang {lang}")
                speech = Speech(words, lang)
                speech.play()
            except Exception as e:
                self.logger.error(f"Error playing text-to-speech audio: {e}")
        else:
            self.logger.warning("google_speech is not available")

    def play_music(
        self, track_path: str, force: bool, start=0.0, volume: Optional[int] = None
    ) -> dict[str, Any]:
        """
        Play a music track.

        Args:
            track_path (str): The file path of the music track to play.
            force (bool): Whether to force the playback if something else is currently playing.

        Returns:
            dict: Information about the music track being played, including whether it is playing, its duration, and its file name.

        Raises:
            FileNotFoundError: If the specified track file does not exist.
        """

        if path.exists(track_path):
            duration = self.music.music_get_duration(track_path)
            track = path.basename(track_path)
            is_playing = self.is_sound_playing()
            if is_playing and not force:
                self.logger.info(f"Stopping currently playing music")
                self.stop_music()
                self.last_response = {
                    "playing": self.is_music_playing(),
                    "duration": duration,
                    "track": track,
                    "start": start,
                }
                return self.last_response
            else:
                if is_playing:
                    self.stop_music()
                if self.is_sound_playing():
                    self.logger.info(f"Stopping currently playing sound")
                    self.stop_sound()
                self.logger.info(f"Playing music {track_path}")
                self.music.music_play(filename=track_path, start=start, volume=volume)
                self.last_response = {
                    "playing": self.is_music_playing(),
                    "duration": duration,
                    "track": track,
                    "start": start,
                }
                return self.last_response
        else:
            text = f"The music file {track_path} is missing."
            self.logger.error(text)
            raise FileNotFoundError(f"No such file or directory: '{text}'")

    def get_music_play_status(self):
        if self.last_response:
            self.last_response["playing"] = self.is_music_playing()
            self.last_response["start"] = self.get_music_pos()
            return self.last_response

    def stop_music(self):
        """
        Stop the currently playing music.

        Returns:
            None
        """

        self.music.music_stop()

    def is_music_playing(self):
        """
        Check if music is currently playing.

        Returns:
            bool: True if music is playing, False otherwise.
        """

        return self.music.pygame.mixer.music.get_busy()

    def get_music_pos(self):
        miliseconds = self.music.pygame.mixer.music.get_pos()
        seconds = max(0.0, miliseconds / 1000)
        return seconds

    def play_sound(self, sound_path: str, force: bool) -> dict[str, Any]:
        """
        Play a sound effect.

        Args:
            sound_path (str): The file path of the sound effect to play.
            force (bool): Whether to force the playback if something else is currently playing.

        Returns:
            dict: Information about the sound effect being played, including whether it is playing, its duration, and its file name.

        Raises:
            FileNotFoundError: If the specified sound file does not exist.
        """

        if path.exists(sound_path):
            duration = self.music.music_get_duration(sound_path)
            track = path.basename(sound_path)
            is_playing = self.is_sound_playing()
            if is_playing and not force:
                self.logger.info(f"Stopping currently playing sound")
                self.stop_sound()
                return {
                    "playing": False,
                    "duration": duration,
                    "track": track,
                }
            else:
                if is_playing and force:
                    self.logger.info(f"Stopping currently playing sound")
                    self.stop_sound()
                if self.is_music_playing():
                    self.logger.info(f"Stopping currently playing music")
                    self.stop_music()
                sound_length = self.music.sound_length(sound_path)
                self.logger.info(
                    f"Playing sound {sound_path} with duration {duration} and length {sound_length}"
                )
                self.music.sound_play_threading(sound_path)
                self.sound_playing = True
                self.sound_end_time = time.time() + sound_length
                return {
                    "playing": True,
                    "duration": duration,
                    "track": track,
                }
        else:
            text = f"The sound file {sound_path} is missing."
            self.logger.error(text)
            raise FileNotFoundError(f"No such file or directory: '{text}'")

    def is_sound_playing(self):
        """
        Check if a sound effect is currently playing.

        Returns:
            bool: True if a sound effect is playing, False otherwise.
        """

        if (
            self.sound_playing
            and self.sound_end_time is not None
            and time.time() >= self.sound_end_time
        ):
            self.sound_playing = False
        return self.sound_playing

    def stop_sound(self):
        """
        Stop the currently playing sound effect.

        Returns:
            None
        """

        self.sound_playing = False
        self.music.pygame.mixer.stop()
