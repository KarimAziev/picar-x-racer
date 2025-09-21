from app.core.logger import Logger
from typing import Dict, List

from app.exceptions.tts import TextToSpeechException
from google_speech_pyplay import LANGUAGES_OPTIONS, Speech

_log = Logger(__name__)


class TTSService:
    """
    The TTSService class provides methods for text-to-speech functionality,
    using Google Translate TTS (Text To Speech) API.
    """

    def __init__(self) -> None:
        """
        Initializes the TTSService instance.
        """
        self.is_playing = False

    @staticmethod
    def available_languages() -> List[Dict[str, str]]:
        return LANGUAGES_OPTIONS

    def text_to_speech(self, words: str, lang="en") -> None:
        """
        Convert the given text to speech and play it.

        Args:
            words (str): The text to convert to speech.
            lang (str): The language of the text. Default is "en".
        """
        _log.info(f"text-to-speech: {words} lang {lang}")
        if self.is_playing:
            raise TextToSpeechException("Already speaking")
        try:
            speech = Speech(words, lang)
            self.is_playing = True
            speech.play()
        except Exception:
            _log.error("Unexpected text to speech error", exc_info=True)
            raise
        finally:
            self.is_playing = False
