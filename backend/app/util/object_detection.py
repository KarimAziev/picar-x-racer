from typing import TYPE_CHECKING, Any, Dict, List, Optional

import cv2
import numpy as np
from app.util.logger import Logger

if TYPE_CHECKING:
    from ultralytics import YOLO

logger = Logger(__name__)


def perform_detection(
    frame: np.ndarray,
    yolo_model: "YOLO",
    labels_to_detect: Optional[List[str]] = None,
    confidence_threshold: float = 0.25,
    verbose: Optional[bool] = False,
) -> List[Dict[str, Any]]:
    """
    Performs detection on the given frame and filters detections by specified labels and confidence.

    Args:
        frame (np.ndarray): The frame on which to perform detection.
        yolo_model: Loaded YOLO model from the ultralytics package.
        labels_to_detect (Optional[List[str]]): List of labels to detect. If None, all detections are returned.
        confidence_threshold (float): Minimum confidence score to include a detection.
        verbose (Optional[bool]): If True, prints/logs detailed information during detection.

    Returns:
        List[Dict[str, Any]]: A list of detection results.
    """
    original_height, original_width = frame.shape[:2]
    resized_height, resized_width = 192, 192
    frame = cv2.resize(frame, (resized_height, resized_width))

    results = yolo_model.predict(
        frame,
        verbose=verbose,
        conf=confidence_threshold,
        task="detect",
        imgsz=(192, 192),
    )[0]

    if verbose:
        logger.info(f"confidence_threshold {confidence_threshold}")

    scale_x = original_width / resized_width
    scale_y = original_height / resized_height

    detection_results = []

    if results.boxes is not None:
        for detection in results.boxes:
            x1, y1, x2, y2 = detection.xyxy[0].tolist()
            conf = detection.conf.item()
            cls = detection.cls.item()
            label = yolo_model.names[int(cls)]

            if conf < confidence_threshold:
                continue

            if labels_to_detect is None or label in labels_to_detect:
                x1 = int(x1 * scale_x)
                y1 = int(y1 * scale_y)
                x2 = int(x2 * scale_x)
                y2 = int(y2 * scale_y)

                detection_results.append(
                    {
                        "bbox": [x1, y1, x2, y2],
                        "label": label,
                        "confidence": conf,
                    }
                )

    return detection_results


def perform_cat_detection(
    frame: np.ndarray,
    yolo_model: "YOLO",
    confidence_threshold: float = 0.5,
    verbose: Optional[bool] = False,
) -> List[Dict[str, Any]]:
    """
    Performs detection for the cat on the given frame.

    Args:
        frame (np.ndarray): The frame on which to perform detection.
        yolo_model: Loaded YOLO model from the ultralytics package.
        confidence_threshold (float): Minimum confidence score to include a detection.

    Returns:
        List[Dict[str, Any]]: A list of detection results.
    """
    return perform_detection(
        frame=frame,
        labels_to_detect=["cat"],
        confidence_threshold=confidence_threshold,
        yolo_model=yolo_model,
        verbose=verbose,
    )


def perform_person_detection(
    frame: np.ndarray,
    yolo_model: "YOLO",
    confidence_threshold: float = 0.5,
    verbose: Optional[bool] = False,
) -> List[Dict[str, Any]]:
    """
    Performs detection for the person on the given frame.

    Args:
        frame (np.ndarray): The frame on which to perform detection.
        yolo_model: Loaded YOLO model from the ultralytics package.
        confidence_threshold (float): Minimum confidence score to include a detection.

    Returns:
        List[Dict[str, Any]]: A list of detection results.
    """
    return perform_detection(
        frame=frame,
        labels_to_detect=["person"],
        confidence_threshold=confidence_threshold,
        yolo_model=yolo_model,
        verbose=verbose,
    )
