from app.robot_hat.music import Music
from app.util.logger import Logger
import time
from os import path
from app.util.singleton_meta import SingletonMeta


try:
    from google_speech import Speech

    google_speech_available = True
except ImportError:
    google_speech_available = False


class AudioController(metaclass=SingletonMeta):
    def __init__(self):
        self.music = Music()
        self.logger = Logger("AudioController")
        self.google_speech_available = google_speech_available
        self.music.music_set_volume(100)
        self.sound_playing = False
        self.sound_end_time = None

    def text_to_speech(self, words: str, lang="en"):
        if google_speech_available:
            try:
                self.logger.info(f"text-to-speech: {words}")
                speech = Speech(words, lang)
                speech.play()
            except Exception as e:
                self.logger.error(f"Error playing text-to-speech audio: {e}")
        else:
            self.logger.warning("google_speech is not available")

    def play_music(self, track_path: str):
        if path.exists(track_path):
            if self.is_music_playing():
                self.logger.info(f"Stopping currently playing music")
                self.stop_music()
            else:
                self.logger.info(f"Playing music {track_path}")
                self.music.music_play(track_path)
        else:
            text = f"The music file {track_path} is missing."
            self.logger.info(text)

    def stop_music(self):
        self.music.music_stop()

    def is_music_playing(self):
        return self.music.pygame.mixer.music.get_busy()

    def play_sound(self, sound_path: str):
        if path.exists(sound_path):
            if self.is_sound_playing():
                self.logger.info(f"Stopping currently playing sound")
                self.stop_sound()
            else:
                self.logger.info(f"Playing sound {sound_path}")
                sound_length = self.music.sound_length(sound_path)
                self.music.sound_play_threading(sound_path)
                self.sound_playing = True
                self.sound_end_time = time.time() + sound_length
        else:
            text = f"The sound file {sound_path} is missing."
            self.logger.info(text)

    def is_sound_playing(self):
        if (
            self.sound_playing
            and self.sound_end_time is not None
            and time.time() >= self.sound_end_time
        ):
            self.sound_playing = False
        return self.sound_playing

    def stop_sound(self):
        self.sound_playing = False
        self.music.pygame.mixer.stop()
