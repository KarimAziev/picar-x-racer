from typing import List, Optional

from pydantic import BaseModel, Field


class TextToSpeechData(BaseModel):
    """
    A model to represent the details required to convert text to speech.

    Attributes:
    - `text`: The text to convert to speech.
    - `lang`: The language of the text. Defaults to None.
    """

    text: str = Field(
        ..., description="The text to convert to speech.", examples=[["Hello world"]]
    )
    lang: Optional[str] = Field(
        None,
        description="The language of the text. Defaults to None.",
        examples=["en", "en-us", "es", "zh-cn", "uk"],
    )


class TextToSpeechItem(BaseModel):
    """
    A model to represent a text to speech item in multiple languages.
    """

    text: str = Field(
        ..., description="The content of the text.", examples=[["Hello world"]]
    )
    language: str = Field(
        ...,
        description="The language in which the text is written (e.g., 'en', 'es').",
        examples=["en", "en-us", "es", "zh-cn", "uk"],
    )
    default: Optional[bool] = Field(
        None, description="Indicator if this text is the default one."
    )


class TTSSettings(BaseModel):
    """
    A model to represent Text-to-Speech (TTS) settings.
    """

    default_tts_language: Optional[str] = Field(
        None,
        description="The default language for TTS output (e.g., 'en' for English).",
        examples=["en", "en-us", "es", "zh-cn", "uk"],
    )
    texts: Optional[List[TextToSpeechItem]] = Field(
        None,
        description="A list of `TextToSpeechItem` representing available TTS items in multiple languages.",
    )
    allowed_languages: Optional[List[str]] = Field(
        None,
        description="A list of enabled language codes.",
        examples=["en", "en-us", "es"],
    )


class LanguageOption(BaseModel):
    """
    A model to represent a language option.
    """

    value: str = Field(
        None,
        description="The language code.",
        examples=["en", "en-us", "es"],
    )
    label: str = Field(
        None,
        description="Human readable description of language.",
        examples=["English", "English (US)", "Spanish"],
    )
