class TextToSpeechException(Exception):
    """Custom exception raised for errors in the Text-to-Speech process."""

    pass


class TextToSpeechRequestError(TextToSpeechException):
    """Raised when a text-to-speech request is invalid."""

    pass


class TextToSpeechUnavailable(TextToSpeechException):
    """Raised when the text-to-speech player cannot accept a request."""

    pass
