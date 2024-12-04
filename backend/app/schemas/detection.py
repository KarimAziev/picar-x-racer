from typing import List, Optional

from pydantic import BaseModel


class DetectionSettings(BaseModel):
    """
    A schema for defining detection configuration settings.

    Attributes:
        model: The name of the object detection model to be used.
        confidence: The confidence threshold for detections.
        active: Flag indicating whether the detection is currently active.
        img_size: The image size for the detection process.
        labels: A list of labels to filter for specific object detections, if desired.
    """

    model: Optional[str] = None
    confidence: Optional[float] = None
    active: Optional[bool] = None
    img_size: int = 640
    labels: Optional[List[str]] = None
