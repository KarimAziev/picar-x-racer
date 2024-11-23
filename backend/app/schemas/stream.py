from typing import List, Optional

from pydantic import BaseModel


class StreamSettings(BaseModel):
    format: str = ".jpg"
    quality: Optional[int] = 100
    enhance_mode: Optional[str] = None
    video_record: Optional[bool] = None
    render_fps: Optional[bool] = None


class EnhancersResponse(BaseModel):
    """
    A model to represent the response for video enhancers.

    Attributes:
    - enhancers: A list of video enhancer names.
    """

    enhancers: List[str]
