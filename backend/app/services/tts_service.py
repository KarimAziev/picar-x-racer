from app.exceptions.tts import TextToSpeechException
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from google_speech_pyplay import LANGUAGES_OPTIONS, Speech


class TTSService(metaclass=SingletonMeta):
    """
    The TTSService class provides methods for text-to-speech functionality,
    using Google Translate TTS (Text To Speech) API.
    """

    def __init__(self):
        """
        Initializes the TTSService instance.
        """
        self.logger = Logger(__name__)
        self.is_playing = False

    @staticmethod
    def available_languages():
        return LANGUAGES_OPTIONS

    def text_to_speech(self, words: str, lang="en") -> None:
        """
        Convert the given text to speech and play it.

        Args:
            words (str): The text to convert to speech.
            lang (str): The language of the text. Default is "en".
        """
        self.logger.info(f"text-to-speech: {words} lang {lang}")
        if self.is_playing:
            raise TextToSpeechException("Already speaking")
        try:
            speech = Speech(words, lang)
            self.is_playing = True
            speech.play()
        except Exception:
            self.logger.error("Unexpected text to speech error", exc_info=True)
            raise
        finally:
            self.is_playing = False
