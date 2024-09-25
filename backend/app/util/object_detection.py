from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np
import torch

if TYPE_CHECKING:
    from ultralytics import YOLO


def perform_detection(
    frame: np.ndarray,
    yolo_model: "YOLO",
    labels_to_detect: Optional[List[str]] = None,
    confidence_threshold: float = 0.25,
) -> List[Dict[str, Any]]:
    """
    Performs detection on the given frame and filters detections by specified labels and confidence.

    Args:
        frame (np.ndarray): The frame on which to perform detection.
        labels_to_detect (Optional[List[str]]): List of labels to detect. If None, all detections are returned.
        confidence_threshold (float): Minimum confidence score to include a detection.

    Returns:
        List[Dict[str, Any]]: A list of detection results.
    """
    with torch.no_grad():
        results = yolo_model(frame)[0]

    detection_results = []

    for detection in results.boxes:
        x1, y1, x2, y2 = detection.xyxy[0].tolist()
        conf = detection.conf.item()
        cls = detection.cls.item()
        label = yolo_model.names[int(cls)]

        if conf < confidence_threshold:
            continue

        if labels_to_detect is None or label in labels_to_detect:
            detection_results.append(
                {
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "label": label,
                    "confidence": conf,
                }
            )

    return detection_results


def perform_cat_detection(
    frame: np.ndarray, yolo_model: "YOLO"
) -> List[Dict[str, Any]]:
    """
    Performs detection for the cat on the given frame.

    Args:
        frame (np.ndarray): The frame on which to perform detection.

    Returns:
        List[Dict[str, Any]]: A list of detection results.
    """
    return perform_detection(
        frame=frame,
        labels_to_detect=["cat"],
        confidence_threshold=0.5,
        yolo_model=yolo_model,
    )


def perform_person_detection(
    frame: np.ndarray, yolo_model: "YOLO"
) -> List[Dict[str, Any]]:
    """
    Performs detection for the person on the given frame.

    Args:
        frame (np.ndarray): The frame on which to perform detection.

    Returns:
        List[Dict[str, Any]]: A list of detection results.
    """
    return perform_detection(
        frame=frame,
        labels_to_detect=["person"],
        confidence_threshold=0.5,
        yolo_model=yolo_model,
    )
