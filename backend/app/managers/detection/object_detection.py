from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import numpy as np
from app.core.logger import Logger
from app.exceptions.detection import DetectionDimensionMismatch
from app.util.video_utils import letterbox

if TYPE_CHECKING:
    from app.adapters.hailo_adapter import YOLOHailoAdapter
    from ultralytics import YOLO

logger = Logger(__name__)


def perform_detection(
    frame: np.ndarray,
    yolo_model: Union["YOLO", "YOLOHailoAdapter"],
    resized_height: int,
    resized_width: int,
    original_width: int,
    original_height: int,
    pad_top: int,
    pad_left: int,
    labels_to_detect: Optional[List[str]] = None,
    confidence_threshold: float = 0.4,
    verbose: Optional[bool] = False,
    should_resize: bool = False,
) -> List[Dict[str, Any]]:
    """
    Performs object detection on a given frame and adjusts detected bounding boxes by undoing the letterbox
    padding before scaling the coordinates back to the original image dimensions.

    When resizing is enabled, the frame is processed by the letterbox function (which returns pad_top and pad_left).
    After detection, each detection's bounding box coordinates are first shifted by subtracting the pad offsets, then scaled.

    Args:
        frame: Input frame.
        yolo_model: The detection model.
        resized_height: Expected height of the image fed to the detection model.
        resized_width: Expected width of the image fed to the detection model.
        original_width: The width of the original frame.
        original_height: The height of the original frame.
        pad_top: The top padding (in pixels) applied during letterbox.
        pad_left: The left padding (in pixels) applied during letterbox.
        labels_to_detect: List of target labels to filter detections.
        confidence_threshold: Minimum confidence for a detection to be considered.
        verbose: Verbosity flag.
        should_resize: If True, the frame is processed using the letterbox function.

    Returns:
        A list of detection dictionaries. Each detection dictionary contains the keys:
            - 'bbox': bounding box coordinates [x1, y1, x2, y2] (mapped to the original image space)
            - 'label': label string
            - 'confidence': confidence score
            - optionally, 'keypoints'
    """
    logger.info("resized_height=%s, resized_width=%s", resized_height, resized_width)

    if should_resize:
        (
            resized_frame,
            original_width,
            original_height,
            resized_width,
            resized_height,
            computed_pad_left,
            computed_pad_top,
        ) = letterbox(frame, expected_w=resized_width, expected_h=resized_height)
        pad_left = computed_pad_left
        pad_top = computed_pad_top
    else:
        resized_frame = frame

    try:
        results = yolo_model.predict(
            source=resized_frame,
            verbose=verbose,
            conf=confidence_threshold,
            task="detect",
            imgsz=resized_width,
        )[0]
    except ValueError as e:
        error_message = str(e)
        if "Dimension mismatch" in error_message:
            logger.error(error_message)
            raise DetectionDimensionMismatch(error_message)
        else:
            raise

    scale_x = original_width / float(resized_width)
    scale_y = original_height / float(resized_height)

    detection_results: List[Dict[str, Any]] = []
    if hasattr(results, "boxes") and results.boxes is not None:
        idx = 0
        keypoints = results.keypoints if results.keypoints is not None else None

        for detection in results.boxes:
            x1, y1, x2, y2 = detection.xyxy[0].tolist()
            conf = round(detection.conf.item(), 2)
            cls = int(detection.cls.item())
            try:
                # Attempt to obtain label from YOLO model's names dictionary.
                label = yolo_model.names[cls]
            except (AttributeError, KeyError):
                # Fall back if that fails (e.g. for a Hailo adapter).
                label = detection._det.get("label", str(cls))
            if conf < confidence_threshold:
                continue

            if not labels_to_detect or not label or label in labels_to_detect:
                x1_adj = x1 - pad_left
                y1_adj = y1 - pad_top
                x2_adj = x2 - pad_left
                y2_adj = y2 - pad_top

                x1_final = int(x1_adj * scale_x)
                y1_final = int(y1_adj * scale_y)
                x2_final = int(x2_adj * scale_x)
                y2_final = int(y2_adj * scale_y)

                detection_entry = {
                    "bbox": [x1_final, y1_final, x2_final, y2_final],
                    "label": label,
                    "confidence": conf,
                }
                if keypoints is not None and idx < len(keypoints):
                    raw_keypoints = keypoints.xy[idx].tolist()
                    formatted_keypoints = [
                        {
                            "x": int((x - pad_left) * scale_x),
                            "y": int((y - pad_top) * scale_y),
                        }
                        for (x, y) in raw_keypoints
                    ]
                    detection_entry["keypoints"] = formatted_keypoints

                detection_results.append(detection_entry)
            idx += 1
    return detection_results
