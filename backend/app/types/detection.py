from typing import List, Literal, Optional, TypedDict, Union

import numpy as np

DetectionProcessCommand = Literal["set_detect_mode"]


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
    labels: Optional[List[str]]
    command: DetectionProcessCommand


class DetectionKeypoint(TypedDict):
    """
    Represents a keypoint in an object detection result.

    Keypoints indicate specific locations within a detected object, such as human joints
    or object reference points.
    """

    x: float
    y: float


class DetectionResult(TypedDict):
    """
    Represents a basic detection result.

    Contains information such as the detected object's bounding box, label, and confidence score.
    """

    bbox: List[float]
    label: str
    confidence: float


class DetectionPoseResult(DetectionResult):
    """
    Represents a detection result with additional pose keypoints.

    This extends the basic detection result by including detected keypoints for pose estimation.
    """

    keypoints: List[DetectionKeypoint]


class DetectionQueueData(TypedDict):
    """
    Represents a message containing detection results.

    This structure is used to communicate detection outcomes, including their timestamps.
    """

    detection_result: List[Union[DetectionResult, DetectionPoseResult]]
    timestamp: float


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

    error: str
    success: bool


class DetectionReadyMessage(TypedDict):
    """
    Represents a message indicating the readiness of the detection process.

    Contains a success flag stating if the detection process is ready for use.
    """

    success: bool
