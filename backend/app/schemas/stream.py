from typing import List, Optional

from pydantic import BaseModel


class StreamSettings(BaseModel):
    """
    Model for video stream settings.

    Attributes:
    --------------
    - `format` (str): The file format to save frames (e.g., `.jpg`, `.png`).
    - `quality` (Optional[int]): Quality compression level for frames (0–100).
    - `enhance_mode` (Optional[str]): Enhancer to apply to frames (e.g., `simulate_predator_vision`).
    - `video_record` (Optional[bool]): Whether the video stream should be recorded.
    - `render_fps` (Optional[bool]): Whether to render the video FPS.
    """

    format: str = ".jpg"
    quality: Optional[int] = 100
    enhance_mode: Optional[str] = None
    video_record: Optional[bool] = None
    render_fps: Optional[bool] = None


class EnhancersResponse(BaseModel):
    """
    A model to represent the response for video enhancers.

    Attributes:
    --------------
    - `enhancers` (List[str]): A list of video enhancer names.

    Example:
    --------------
    ```json
    {
        "enhancers": [
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
            "preprocess_frame_combined"
        ]
    }
    ```
    """

    enhancers: List[str]
