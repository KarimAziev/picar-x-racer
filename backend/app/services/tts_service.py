from app.exceptions.tts import TextToSpeechException
from app.util.logger import Logger
from app.util.singleton_meta import SingletonMeta
from google_speech_pyplay import Speech


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

    def text_to_speech(self, words: str, lang="en") -> None:
        """
        Convert the given text to speech and play it.

        Args:
            words (str): The text to convert to speech.
            lang (str): The language of the text. Default is "en".
        """
        self.logger.info(f"text-to-speech: {words} lang {lang}")
        try:
            speech = Speech(words, lang)
            speech.play()
        except Exception as e:
            self.logger.error("Text to speech error: %s", e)
            raise TextToSpeechException("Text to speech error") from e
