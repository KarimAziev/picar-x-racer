from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np
from app.core.logger import Logger
from app.exceptions.detection import DetectionDimensionMismatch
from app.util.video_utils import resize_to_fixed_height

if TYPE_CHECKING:
    from ultralytics import YOLO

logger = Logger(__name__)


def perform_detection(
    frame: np.ndarray,
    yolo_model: "YOLO",
    resized_height: int,
    resized_width: int,
    original_width: int,
    original_height: int,
    labels_to_detect: Optional[List[str]] = None,
    confidence_threshold: float = 0.4,
    verbose: Optional[bool] = False,
    should_resize=False,
) -> List[Dict[str, Any]]:
    """
    Performs object detection on a given frame and filters the results based on specified labels and confidence thresholds.

    Args:
        frame: The frame (image data) on which object detection is performed.
        yolo_model: The pre-loaded YOLO model from the ultralytics package.
        resized_height: The height of the frame after resizing, used for YOLO detection.
        resized_width: The width of the frame after resizing, used for YOLO detection.
        original_width: The original width of the frame before resizing.
        original_height: The original height of the frame before resizing.
        labels_to_detect: A list of target labels to filter the detection results. If `None`, all detections are returned.
        confidence_threshold: The minimum confidence level required for a detection to be valid. Default is 0.4.
        verbose: If `True`, logs detailed information about the detection process. Optional.
        should_resize: A flag indicating whether the input frame should be resized before detection. Defaults to `False`.

    Returns:
        A list of detection results, where each result is a dictionary containing:
            - `bbox`: A list of bounding box coordinates [x1, y1, x2, y2].
            - `label`: The label (class name) of the detected object.
            - `confidence`: The confidence score of the detection.

    Behavior:
        - If resizing is enabled, adjusts the frame size and calculates scaling factors.
        - Performs detection using the YOLO model.
        - Applies scaling to map detected bounding boxes to the original frame dimensions.
        - Filters detections based on confidence threshold and specified labels.
    """
    (
        resized_frame,
        original_width,
        original_height,
        resized_width,
        resized_height,
    ) = (
        resize_to_fixed_height(frame, base_size=resized_height)
        if should_resize
        else (frame, original_width, original_height, resized_width, resized_height)
    )

    try:
        results = yolo_model.predict(
            source=resized_frame,
            verbose=verbose,
            conf=confidence_threshold,
            task="detect",
            imgsz=resized_height,
        )[0]
    except ValueError as e:
        error_message = str(e)
        if "Dimension mismatch" in error_message:
            logger.error(error_message)
            raise DetectionDimensionMismatch(error_message)
        else:
            raise

    scale_x = original_width / resized_width
    scale_y = original_height / resized_height

    detection_results = []

    if results.boxes is not None:
        boxes = results.boxes
        keypoints = results.keypoints if results.keypoints is not None else None

        idx = 0

        for detection in boxes:
            x1, y1, x2, y2 = detection.xyxy[0].tolist()
            conf = round(detection.conf.item(), 2)
            cls = int(detection.cls.item())
            label = yolo_model.names[cls]

            if conf < confidence_threshold:
                continue

            if not labels_to_detect or label in labels_to_detect:
                x1 = int(x1 * scale_x)
                y1 = int(y1 * scale_y)
                x2 = int(x2 * scale_x)
                y2 = int(y2 * scale_y)

                detection_entry = {
                    "bbox": [x1, y1, x2, y2],
                    "label": label,
                    "confidence": conf,
                }

                if keypoints is not None and idx < len(keypoints):
                    raw_keypoints = keypoints.xy[idx].tolist()

                    formatted_keypoints = [
                        {"x": int(x * scale_x), "y": int(y * scale_y)}
                        for (x, y), in zip(raw_keypoints)
                        if x > 0 and y > 0
                    ]

                    detection_entry["keypoints"] = formatted_keypoints

                detection_results.append(detection_entry)

            idx += 1

    return detection_results
