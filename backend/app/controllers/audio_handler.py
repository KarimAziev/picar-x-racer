from app.robot_hat.music import Music
import time
from os import path
from app.util.singleton_meta import SingletonMeta


try:
    from google_speech import Speech

    google_speech_available = True
except ImportError:
    google_speech_available = False


class AudioHandler(metaclass=SingletonMeta):
    def __init__(self):
        self.music = Music()
        self.music.music_set_volume(100)
        self.sound_playing = False
        self.sound_end_time = None

    def text_to_speech(self, words: str, lang="en"):
        if google_speech_available:
            try:
                print(f"Playing text-to-speech for: {words}")
                speech = Speech(words, lang)
                speech.play()
            except Exception as e:
                print(f"Error playing text-to-speech audio: {e}")
        else:
            print(
                f"google_speech not available. Unable to play text-to-speech for: {words}"
            )

    def play_music(self, track_path: str):
        if path.exists(track_path):
            if self.is_music_playing():
                print(f"Stopping currently playing music")
                self.stop_music()
            else:
                print(f"Playing music {track_path}")
                self.music.music_play(track_path)
        else:
            text = f"The music file {track_path} is missing."
            print(text)
            self.text_to_speech(text, "en")

    def stop_music(self):
        self.music.music_stop()

    def is_music_playing(self):
        return self.music.pygame.mixer.music.get_busy()

    def play_sound(self, sound_path: str):
        if path.exists(sound_path):
            if self.is_sound_playing():
                print(f"Stopping currently playing sound")
                self.stop_sound()
            else:
                print(f"Playing sound {sound_path}")
                sound_length = self.music.sound_length(sound_path)
                self.music.sound_play_threading(sound_path)
                self.sound_playing = True
                self.sound_end_time = time.time() + sound_length
        else:
            text = f"The sound file {sound_path} is missing."
            print(text)
            self.text_to_speech(text, "en")

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
