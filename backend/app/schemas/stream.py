from typing import List, Optional

from app.config.video_enhancers import frame_enhancers
from pydantic import BaseModel, Field


class StreamSettings(BaseModel):
    """
    Model for video stream settings.

    Attributes:
    --------------
    - `format`: The file format to save frames (e.g., `.jpg`, `.png`).
    - `quality`: Quality compression level for frames (0–100).
    - `enhance_mode`: Video effect to apply to frames.
    - `video_record`: Whether the video stream should be recorded.
    - `render_fps`: Whether to render the video FPS.
    """

    format: str = Field(
        ".jpg", description="The file format to save frames (e.g., `.jpg`, `.png`)."
    )
    quality: Optional[int] = Field(
        100, ge=0, le=100, description="Quality compression level for frames (0–100)."
    )
    enhance_mode: Optional[str] = Field(
        None,
        description="Enhancer to apply to frames (e.g., `robocop_vision`).",
        examples=list(frame_enhancers.keys()),
    )
    video_record: Optional[bool] = Field(
        None, description="Whether the video stream should be recorded."
    )
    render_fps: Optional[bool] = Field(
        None, description="Whether to render the video FPS."
    )


class EnhancersResponse(BaseModel):
    """
    A model to represent the response for video enhancers.
    """

    enhancers: List[str] = Field(
        ...,
        description="A list of video enhancer names.",
        examples=[
            list(frame_enhancers.keys()),
        ],
    )
