from typing import List, Optional

from pydantic import BaseModel, Field


class StreamSettings(BaseModel):
    """
    Model for video stream settings.

    Attributes:
    --------------
    - `format`: The file format to save frames (e.g., `.jpg`, `.png`).
    - `quality`: Quality compression level for frames (0–100).
    - `enhance_mode`: Enhancer to apply to frames (e.g., `simulate_predator_vision`).
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
        description="Enhancer to apply to frames (e.g., `simulate_predator_vision`).",
        examples=[
            "simulate_robocop_vision",
            "simulate_predator_vision",
            "simulate_infrared_vision",
            "simulate_ultrasonic_vision",
            "preprocess_frame",
            "preprocess_frame_clahe",
            "preprocess_frame_edge_enhancement",
            "preprocess_frame_ycrcb",
            "preprocess_frame_hsv_saturation",
            "preprocess_frame_kmeans",
            "preprocess_frame_combined",
        ],
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
            [
                "simulate_robocop_vision",
                "simulate_predator_vision",
                "simulate_infrared_vision",
                "simulate_ultrasonic_vision",
                "preprocess_frame",
                "preprocess_frame_clahe",
                "preprocess_frame_edge_enhancement",
                "preprocess_frame_ycrcb",
                "preprocess_frame_hsv_saturation",
                "preprocess_frame_kmeans",
                "preprocess_frame_combined",
            ]
        ],
    )
