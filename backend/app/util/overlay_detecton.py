import cv2
import numpy as np
from typing_extensions import Any


def overlay_detection(frame: np.ndarray, detection_result: Any) -> np.ndarray:
    """
    Overlays detection results onto the frame.

    Args:
        frame (np.ndarray): The current video frame.
        detection_result (Any): The detection results obtained from the detection process.

    Returns:
        np.ndarray: The frame with detection overlays.
    """
    for detection in detection_result:
        x1, y1, x2, y2 = detection["bbox"]
        label = detection["label"]
        confidence = detection["confidence"]

        cv2.rectangle(frame, (x1, y1), (x2, y2), color=(191, 255, 0), thickness=2)

        cv2.putText(
            frame,
            f"{label}: {confidence:.2f}",
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (191, 255, 0),
            2,
        )
    return frame
