from typing import List, Optional

from app.config.video_enhancers import frame_enhancers
from pydantic import BaseModel, Field
from typing_extensions import Annotated


class StreamSettings(BaseModel):
    """
    Model for video stream settings.
    """

    format: Annotated[
        str,
        Field(
            ..., description="The file format to save frames (e.g., `.jpg`, `.png`)."
        ),
    ] = ".jpg"
    quality: Annotated[
        Optional[int],
        Field(
            ...,
            ge=0,
            le=100,
            description="Quality compression level for frames (0–100).",
        ),
    ] = 100
    enhance_mode: Annotated[
        Optional[str],
        Field(
            ...,
            description="Enhancer to apply to frames (e.g., `robocop_vision`).",
            examples=list(frame_enhancers.keys()),
        ),
    ] = None
    video_record: Annotated[
        Optional[bool],
        Field(..., description="Whether the video stream should be recorded."),
    ] = None
    render_fps: Annotated[
        Optional[bool], Field(..., description="Whether to render the video FPS.")
    ] = None

    auto_stop_camera_on_disconnect: Annotated[
        bool,
        Field(
            ...,
            description="If set to True, the camera will be auto-stopped when the last websocket client disconnects.",
        ),
    ] = True


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
