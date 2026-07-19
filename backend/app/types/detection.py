from typing import Dict, List, Literal, Optional, TypedDict, Union

import numpy as np
from typing_extensions import NotRequired

DetectionProcessCommand = Literal["set_detect_mode"]
SegmentationDetail = Literal["fast", "balanced", "detailed"]


class DetectionFrameData(TypedDict):
    """
    Represents the frame data for object detection.

    This includes metadata such as frame dimensions, padding applied during resizing,
    and whether resizing should be performed.
    """

    frame: np.ndarray
    timestamp: float
    original_height: int
    original_width: int
    resized_height: int
    resized_width: int
    pad_left: int
    pad_top: int
    should_resize: bool


class DetectionControlMessage(TypedDict):
    """
    Represents a message to control the detection process.

    This can include settings like detection confidence, specific labels to detect,
    and commands to modify the detection operation.
    """

    confidence: Optional[float]
    iou_threshold: NotRequired[Optional[float]]
    max_detections: NotRequired[Optional[int]]
    labels: Optional[List[str]]
    segmentation_detail: NotRequired[SegmentationDetail]
    command: DetectionProcessCommand


class DetectionKeypoint(TypedDict):
    """
    Represents a keypoint in an object detection result.

    Keypoints indicate specific locations within a detected object, such as human joints
    or object reference points.
    """

    x: float
    y: float
    confidence: NotRequired[float]


DetectionSegment = List[DetectionKeypoint]


class DetectionResult(TypedDict):
    """
    Represents a basic detection result.

    Contains information such as the detected object's bounding box, label, and confidence score.
    """

    bbox: List[float]
    label: str
    confidence: float


class DetectionSegmentResult(DetectionResult):
    """
    Represents a detection result with instance segmentation polygons.

    The segments list contains one or more polygons, each represented as x/y
    points mapped to the original frame coordinate space.
    """

    segments: List[DetectionSegment]


class SemanticMaskData(TypedDict):
    """
    Compact run-length encoded semantic segmentation class map.
    """

    width: int
    height: int
    counts: List[List[int]]
    classes: Dict[int, str]


class DetectionPoseResult(DetectionResult):
    """
    Represents a detection result with additional pose keypoints.

    This extends the basic detection result by including detected keypoints for pose estimation.
    """

    keypoints: List[DetectionKeypoint]


DetectionResults = List[
    Union[DetectionResult, DetectionPoseResult, DetectionSegmentResult]
]


class DetectionProcessOutput(TypedDict):
    """
    Represents the output of a single detection process inference.
    """

    detection_result: DetectionResults
    semantic_mask: NotRequired[SemanticMaskData]


class DetectionQueueData(TypedDict):
    """
    Represents a message containing detection results.

    This structure is used to communicate detection outcomes, including their timestamps.
    """

    detection_result: DetectionResults
    timestamp: float
    semantic_mask: NotRequired[SemanticMaskData]


class DetectionResultData(DetectionQueueData):
    """
    Represents extended detection result data.

    This includes an optional flag indicating if the detection process is still loading.
    """

    loading: Optional[bool]


class DetectionErrorMessage(TypedDict):
    """
    Represents an error message from the detection process.

    Contains the error description to help diagnose detection failures.
    """

    error: str


class DetectionLoadErrorMessage(DetectionErrorMessage):
    """
    Represents an error message related to loading a detection model.

    Provides additional information on whether the model loading operation was successful.
    """

    success: bool


class DetectionReadyMessage(TypedDict):
    """
    Represents a message indicating the readiness of the detection process.

    Contains a success flag stating if the detection process is ready for use.
    """

    success: bool
    labels: NotRequired[List[str]]
