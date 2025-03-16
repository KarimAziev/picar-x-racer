from __future__ import annotations

from enum import Enum
from typing import List, Optional

from app.util.doc_util import extract_clean_docstring
from pydantic import BaseModel, Field, field_validator, model_validator


class OverlayStyle(str, Enum):
    """
    An enumeration to represent the detection overlay styles.

    Enum Values:
    - **box**: Draws a bounding box for the detected objects.
    - **aim**: Draws crosshair lines within the detected objects.
    - **mixed**: Draws crosshair lines within the first detection, and for others, a bounding box.
    - **pose**`: Draws keypoints representing specific body joints without boxes.
              Requires pose estimation model, i.e. yolo11n-pose.pt.
    """

    BOX = "box"
    AIM = "aim"
    MIXED = "mixed"
    POSE = "pose"


class DetectionSettings(BaseModel):
    """
    A schema for defining detection configuration settings.
    """

    model: Optional[str] = Field(
        None,
        description="The name of the object detection model to be used. For examples: 'yolov8n.pt'.",
        examples=["yolov8n.pt", "yolo11n.pt", "yolo11m.pt"],
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="The confidence threshold for detections, between 0.0 and 1.0.",
        examples=[0.4],
    )
    active: bool = Field(
        False,
        description="Flag indicating whether the detection is currently active.",
    )
    img_size: int = Field(
        640,
        description=(
            "The image resolution size for the detection process."
            "Should be rounded up to the nearest multiple of 32."
        ),
        examples=[320, 256, 640],
    )
    labels: Optional[List[str]] = Field(
        None,
        description="A list of labels to filter for specific object detections, if desired.",
        examples=[["person", "cat"]],
    )
    overlay_draw_threshold: float = Field(
        1.0,
        gt=0,
        description=(
            "The maximum allowable time difference (in seconds) between the frame timestamp "
            "and the detection timestamp for overlay drawing to occur. Must be greater than 0."
        ),
        examples=[1.0],
    )
    overlay_style: OverlayStyle = Field(
        OverlayStyle.BOX,
        description=extract_clean_docstring(OverlayStyle),
        examples=[OverlayStyle.AIM.value],
    )

    @model_validator(mode="after")
    def validate_active_model_dependency(self) -> "DetectionSettings":
        """
        Ensures that if 'active' is True, 'model' is not None.
        """
        if self.active and self.model is None:
            raise ValueError(
                "A valid detection model (e.g., 'yolov8n.pt')` is required for activating detection."
            )
        return self

    @field_validator("img_size", mode="before")
    def validate_img_size(cls, img_size: int) -> int:
        """
        Validates that `img_size` is an integer rounded up to the nearest multiple of 32.
        """
        MIN_SIZE = 32

        def round_up_to_multiple(value: int, multiple: int = 32) -> int:
            """Rounds a value up to the nearest multiple of a given number."""
            return ((value + multiple - 1) // multiple) * multiple

        if isinstance(img_size, int):
            if img_size < MIN_SIZE:
                raise ValueError(f"`img_size` must be at least {MIN_SIZE}.")
            return round_up_to_multiple(img_size)
