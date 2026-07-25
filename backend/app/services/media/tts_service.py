"""Application service for interruptible text-to-speech playback."""

from app.core.logger import Logger
from app.exceptions.tts import TextToSpeechRequestError, TextToSpeechUnavailable
from gspeech import (
    GSpeechError,
    LanguageOption,
    SpeechHandle,
    SpeechPlayer,
    SpeechPolicy,
    available_languages,
)

_log = Logger(__name__)


class TTSService:
    """Submit, interrupt, and stop Google Translate text-to-speech playback."""

    def __init__(self, player: SpeechPlayer | None = None) -> None:
        self._player = player if player is not None else SpeechPlayer()

    @staticmethod
    def available_languages() -> tuple[LanguageOption, ...]:
        """Return supported languages in the format expected by the API."""
        return available_languages()

    @property
    def is_playing(self) -> bool:
        """Return whether the player is currently producing audio."""
        return self._player.is_playing

    def speak(self, text: str, lang: str = "en") -> SpeechHandle:
        """
        Submit speech without blocking.

        A new request replaces any active or queued speech. The returned handle
        can be used by non-HTTP callers to observe or cancel this request.
        """
        try:
            handle = self._player.speak(
                text,
                lang,
                policy=SpeechPolicy.REPLACE,
            )
        except ValueError as error:
            raise TextToSpeechRequestError(str(error)) from error
        except GSpeechError as error:
            raise TextToSpeechUnavailable(str(error)) from error

        _log.info(
            "Text-to-speech request accepted: id=%s lang=%s chars=%d",
            handle.id,
            handle.lang,
            len(handle.text),
        )
        return handle

    def text_to_speech(self, text: str, lang: str = "en") -> SpeechHandle:
        """Backward-compatible alias for :meth:`speak`."""
        return self.speak(text, lang)

    def stop(
        self,
        *,
        wait: bool = False,
        timeout: float | None = None,
    ) -> bool:
        """Interrupt active speech and discard any pending request."""
        stopped = self._player.stop(wait=wait, timeout=timeout)
        _log.info("Text-to-speech stop requested: interrupted=%s", stopped)
        return stopped

    def close(self, *, timeout: float | None = None) -> None:
        """Release the player and its worker resources."""
        self._player.close(timeout=timeout)
