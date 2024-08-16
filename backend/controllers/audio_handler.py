from os import path
from util.platform_adapters import Music

try:
    from google_speech import Speech

    google_speech_available = True
except ImportError:
    google_speech_available = False


class SingletonMeta(type):
    """
    This is a thread-safe implementation of Singleton.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class AudioHandler(metaclass=SingletonMeta):
    def __init__(self):
        self.music = Music()
        self.music.music_set_volume(100)

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
            print(f"Playing music {track_path}")
            self.music.music_play(track_path)
        else:
            text = f"The music file {track_path} is missing."
            print(text)
            self.text_to_speech(text, "en")

    def stop_music(self):
        self.music.music_stop()

    def play_sound(self, sound_path: str):
        if path.exists(sound_path):
            print(f"Playing sound {sound_path}")
            self.music.sound_play(sound_path)
        else:
            text = f"The sound file {sound_path} is missing."
            print(text)
            self.text_to_speech(text, "en")
