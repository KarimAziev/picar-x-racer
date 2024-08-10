from google_speech import Speech
from os import path, uname

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
        self.is_os_raspbery = uname().nodename == "raspberrypi"
        if self.is_os_raspbery:
            print("OS is raspberrypi")
            from robot_hat import Music
        else:
            from stubs import FakeMusic as Music
        self.music = Music()
        self.music.music_set_volume(100)

    def text_to_speech(self, words: str, lang="en"):
        try:
            print(f"Playing text-to-speech for: {words}")
            speech = Speech(words, lang)
            speech.play()
        except Exception as e:
            print(f"Error playing text-to-speech audio: {e}")

    def play_music(self, track_path: str):
        if path.exists(track_path):
            print(f"Playing music {track_path}")
            self.music.music_play(track_path)
        else:
            text = f'The music file {track_path} is missing.'
            print(text)
            self.text_to_speech(text, "en")

    def stop_music(self):
        self.music.music_stop()

    def play_sound(self, sound_path: str):
        if path.exists(sound_path):
            print(f"Playing sound {sound_path}")
            self.music.sound_play(sound_path)
        else:
            text = f'The sound file {sound_path} is missing.'
            print(text)
            self.text_to_speech(text, "en")
