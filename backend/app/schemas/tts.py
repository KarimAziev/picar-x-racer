from typing import Optional

from pydantic import BaseModel


class TextToSpeechData(BaseModel):
    """
    A model to represent the details required to convert text to speech.

    Attributes:
    - `text` (str): The text to convert to speech.
    - `lang` (Optional[str]): The language of the text. Defaults to None.
    """

    text: str
    lang: Optional[str] = None
