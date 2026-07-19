from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional

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
    - **bbox-segment**`: Draws instance segmentation masks with bounding boxes.
              Requires segmentation model, i.e. yolo11n-seg.pt.
    - **no-bbox-segment**`: Draws instance segmentation masks without bounding boxes or labels.
              Requires segmentation model, i.e. yolo11n-seg.pt.
    - **semantic**`: Draws a dense semantic segmentation class map.
              Requires semantic segmentation model, i.e. yolo26n-sem.pt.
    """

    BOX = "box"
    AIM = "aim"
    MIXED = "mixed"
    POSE = "pose"
    BBOX_SEGMENT = "bbox-segment"
    NO_BBOX_SEGMENT = "no-bbox-segment"
    SEMANTIC = "semantic"


class SegmentationDetail(str, Enum):
    """
    Segmentation overlay detail level.

    Enum Values:
    - **fast**: Favors smaller payloads and faster rendering.
    - **balanced**: Default balance between detail and rendering cost.
    - **detailed**: Keeps more segmentation detail at higher rendering cost.
    """

    FAST = "fast"
    BALANCED = "balanced"
    DETAILED = "detailed"


class DetectionModelTask(str, Enum):
    DETECT = "detect"
    POSE = "pose"
    INSTANCE_SEGMENTATION = "instance-segmentation"
    SEMANTIC_SEGMENTATION = "semantic-segmentation"


class DetectionModelSettings(BaseModel):
    """Settings persisted independently for each detection model."""

    confidence: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="The confidence threshold for object detections.",
    )
    iou_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="IoU threshold used by non-maximum suppression.",
    )
    max_detections: int = Field(
        default=300,
        ge=1,
        le=10000,
        description="Maximum number of detections returned for one image.",
    )
    img_size: int = Field(
        default=320,
        description=(
            "The image resolution size for the detection process."
            "Should be rounded up to the nearest multiple of 32."
        ),
        examples=[320, 256, 640],
    )
    labels: Optional[List[str]] = Field(
        default_factory=list,
        description="Labels to include, or an empty list to include every label.",
    )
    available_labels: List[str] = Field(
        default_factory=list,
        description="Labels reported by the model for UI completion.",
    )
    overlay_draw_threshold: float = Field(
        default=1.0,
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
    segmentation_detail: SegmentationDetail = Field(
        default=SegmentationDetail.BALANCED,
        description=extract_clean_docstring(SegmentationDetail),
        examples=[SegmentationDetail.BALANCED.value],
    )
    keypoint_confidence_threshold: float = Field(
        default=0.02,
        ge=0.0,
        le=1.0,
        description="Minimum confidence required to render an individual pose keypoint.",
    )

    @field_validator("img_size", mode="before")
    def validate_img_size(cls, img_size: int) -> int:
        """Round image size up to a supported multiple of 32."""
        min_size = 32

        if isinstance(img_size, int):
            if img_size < min_size:
                raise ValueError(f"`img_size` must be at least {min_size}.")
            return ((img_size + 31) // 32) * 32
        return img_size


class DetectionSettings(DetectionModelSettings):
    """
    A schema for defining detection configuration settings.
    """

    model: Optional[str] = Field(
        None,
        description="The name of the object detection model to be used. For examples: 'yolov8n.pt'.",
        examples=["yolov8n.pt", "yolo11n.pt", "yolo11m.pt"],
    )
    active: bool = Field(
        default=False,
        description="Flag indicating whether the detection is currently active.",
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


class DetectionProfilesConfig(BaseModel):
    """Versioned persisted model profiles and the last selected model."""

    schema_version: Literal[2] = 2
    selected_model: Optional[str] = None
    profiles: Dict[str, DetectionModelSettings] = Field(default_factory=dict)
