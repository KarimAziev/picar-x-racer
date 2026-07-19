from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union, cast

import cv2
import numpy as np
from app.core.logger import Logger
from app.exceptions.detection import DetectionDimensionMismatch
from app.types.detection import (
    DetectionKeypoint,
    DetectionPoseResult,
    DetectionProcessOutput,
    DetectionResult,
    DetectionResults,
    DetectionSegment,
    DetectionSegmentResult,
    SegmentationDetail,
    SemanticMaskData,
)
from app.util.video_utils import letterbox

if TYPE_CHECKING:
    from app.adapters.hailo_adapter import YOLOHailoAdapter

    try:
        from ultralytics import YOLO  # type: ignore[reportPrivateImportUsage]
    except Exception:
        from ultralytics.models.yolo import YOLO

_log = Logger(__name__)

SEGMENT_SIMPLIFICATION_EPSILON_RATIOS = (
    0.001,
    0.002,
    0.004,
    0.008,
    0.012,
    0.016,
    0.02,
)
MAX_SEGMENT_POINTS = 192
SEGMENT_MAX_POINTS_BY_DETAIL: Dict[SegmentationDetail, int] = {
    "fast": 96,
    "balanced": 192,
    "detailed": 384,
}
SEMANTIC_MAX_SIDE_BY_DETAIL: Dict[SegmentationDetail, int] = {
    "fast": 160,
    "balanced": 256,
    "detailed": 384,
}


def _scale_detection_point(
    x: Union[float, int],
    y: Union[float, int],
    pad_left: int,
    pad_top: int,
    scale_x: float,
    scale_y: float,
    confidence: Optional[float] = None,
) -> DetectionKeypoint:
    point: DetectionKeypoint = {
        "x": int((float(x) - pad_left) * scale_x),
        "y": int((float(y) - pad_top) * scale_y),
    }
    if confidence is not None:
        point["confidence"] = round(float(confidence), 4)
    return point


def _scale_detection_segment(
    segment: np.ndarray,
    pad_left: int,
    pad_top: int,
    scale_x: float,
    scale_y: float,
    segmentation_detail: SegmentationDetail,
) -> DetectionSegment:
    points = _simplify_detection_segment(segment, segmentation_detail)
    return [
        _scale_detection_point(x, y, pad_left, pad_top, scale_x, scale_y)
        for x, y in points
    ]


def _simplify_detection_segment(
    segment: np.ndarray,
    segmentation_detail: SegmentationDetail,
) -> List[List[float]]:
    points = np.asarray(segment, dtype=np.float32).reshape(-1, 2)
    max_segment_points = SEGMENT_MAX_POINTS_BY_DETAIL.get(
        segmentation_detail, MAX_SEGMENT_POINTS
    )
    if len(points) <= max_segment_points:
        return points.tolist()

    contour = points.reshape(-1, 1, 2)
    perimeter = cv2.arcLength(contour, closed=True)
    for ratio in SEGMENT_SIMPLIFICATION_EPSILON_RATIOS:
        simplified = cv2.approxPolyDP(contour, epsilon=ratio * perimeter, closed=True)
        simplified_points = simplified.reshape(-1, 2)
        if 3 <= len(simplified_points) <= max_segment_points:
            return simplified_points.tolist()

    indices = np.linspace(
        0,
        len(points) - 1,
        num=min(max_segment_points, len(points)),
        dtype=np.int32,
    )
    return points[np.unique(indices)].tolist()


def _tensor_to_numpy(data: Any) -> np.ndarray:
    if hasattr(data, "detach"):
        data = data.detach()
    if hasattr(data, "cpu"):
        data = data.cpu()
    if hasattr(data, "numpy"):
        data = data.numpy()
    return np.asarray(data)


def _extract_model_names(results: Any, yolo_model: Any) -> Dict[int, str]:
    raw_names = getattr(results, "names", None) or getattr(yolo_model, "names", {})
    names: Dict[int, str] = {}
    if isinstance(raw_names, dict):
        for key, value in raw_names.items():
            try:
                names[int(key)] = str(value)
            except (TypeError, ValueError):
                continue
    return names


def _rle_encode_class_map(class_map: np.ndarray) -> List[List[int]]:
    flat = np.asarray(class_map).reshape(-1)
    if flat.size == 0:
        return []

    counts: List[List[int]] = []
    current_class = int(flat[0])
    current_count = 1
    for raw_class_id in flat[1:]:
        class_id = int(raw_class_id)
        if class_id == current_class:
            current_count += 1
        else:
            counts.append([current_class, current_count])
            current_class = class_id
            current_count = 1
    counts.append([current_class, current_count])
    return counts


def _semantic_classes_for_labels(
    classes: Dict[int, str],
    labels_to_detect: Optional[List[str]],
) -> Dict[int, str]:
    if not labels_to_detect:
        return classes
    allowed_labels = set(labels_to_detect)
    return {
        class_id: label
        for class_id, label in classes.items()
        if label in allowed_labels
    }


def _crop_letterbox_padding(
    class_map: np.ndarray,
    input_shape: Tuple[int, int],
    resized_width: int,
    resized_height: int,
    pad_left: int,
    pad_top: int,
) -> np.ndarray:
    mask_height, mask_width = class_map.shape[:2]
    input_height, input_width = input_shape
    if input_width <= 0 or input_height <= 0:
        return class_map

    x0 = int(round(pad_left * mask_width / float(input_width)))
    y0 = int(round(pad_top * mask_height / float(input_height)))
    x1 = int(round((pad_left + resized_width) * mask_width / float(input_width)))
    y1 = int(round((pad_top + resized_height) * mask_height / float(input_height)))

    x0 = max(0, min(mask_width, x0))
    y0 = max(0, min(mask_height, y0))
    x1 = max(x0 + 1, min(mask_width, x1))
    y1 = max(y0 + 1, min(mask_height, y1))
    return class_map[y0:y1, x0:x1]


def _resize_semantic_map(
    class_map: np.ndarray,
    original_width: int,
    original_height: int,
    segmentation_detail: SegmentationDetail,
) -> np.ndarray:
    max_side = SEMANTIC_MAX_SIDE_BY_DETAIL.get(segmentation_detail, 256)
    scale = min(1.0, max_side / float(max(original_width, original_height)))
    target_width = max(1, int(round(original_width * scale)))
    target_height = max(1, int(round(original_height * scale)))

    if class_map.shape[1] == target_width and class_map.shape[0] == target_height:
        return class_map

    return cv2.resize(
        class_map,
        (target_width, target_height),
        interpolation=cv2.INTER_NEAREST,
    )


def _extract_semantic_mask(
    results: Any,
    yolo_model: Any,
    input_shape: Tuple[int, int],
    resized_width: int,
    resized_height: int,
    original_width: int,
    original_height: int,
    pad_left: int,
    pad_top: int,
    labels_to_detect: Optional[List[str]],
    segmentation_detail: SegmentationDetail,
) -> Optional[SemanticMaskData]:
    semantic_mask = getattr(results, "semantic_mask", None)
    if semantic_mask is None or not hasattr(semantic_mask, "data"):
        return None

    class_map = _tensor_to_numpy(semantic_mask.data)
    while class_map.ndim > 2 and class_map.shape[0] == 1:
        class_map = class_map[0]
    if class_map.ndim > 2:
        class_map = np.squeeze(class_map)
    if class_map.ndim != 2 or class_map.size == 0:
        return None

    cropped_map = _crop_letterbox_padding(
        class_map,
        input_shape,
        resized_width,
        resized_height,
        pad_left,
        pad_top,
    )
    resized_map = _resize_semantic_map(
        cropped_map,
        original_width,
        original_height,
        segmentation_detail,
    ).astype(np.int32, copy=False)

    counts = _rle_encode_class_map(resized_map)
    if not counts:
        return None

    observed_classes = {int(class_id) for class_id in np.unique(resized_map)}
    classes = _extract_model_names(results, yolo_model)
    if not labels_to_detect:
        classes = {
            class_id: classes.get(class_id, str(class_id))
            for class_id in observed_classes
        }
    classes = _semantic_classes_for_labels(classes, labels_to_detect)
    return {
        "width": int(resized_map.shape[1]),
        "height": int(resized_map.shape[0]),
        "counts": counts,
        "classes": classes,
    }


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
    segmentation_detail: SegmentationDetail = "balanced",
) -> DetectionProcessOutput:
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
        A dictionary with object/pose/instance segmentation detections and,
        for semantic segmentation models, a compact dense class map.
    """

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
        prediction_results = cast(
            Any,
            yolo_model.predict(
                source=resized_frame,
                verbose=verbose,
                conf=confidence_threshold,
                imgsz=resized_width,
            ),
        )
        results = prediction_results[0]
    except ValueError as e:
        error_message = str(e)
        if "Dimension mismatch" in error_message:
            _log.error(error_message)
            raise DetectionDimensionMismatch(error_message)
        else:
            raise

    scale_x = original_width / float(resized_width)
    scale_y = original_height / float(resized_height)

    detection_results: DetectionResults = []
    if hasattr(results, "boxes") and results.boxes is not None:
        idx = 0
        keypoints = getattr(results, "keypoints", None)
        masks = getattr(results, "masks", None)
        mask_segments = getattr(masks, "xy", []) if masks is not None else []

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

                detection_entry: Union[
                    DetectionResult, DetectionPoseResult, DetectionSegmentResult
                ] = {
                    "bbox": [x1_final, y1_final, x2_final, y2_final],
                    "label": label,
                    "confidence": conf,
                }

                if idx < len(mask_segments):
                    segment = _scale_detection_segment(
                        mask_segments[idx],
                        pad_left,
                        pad_top,
                        scale_x,
                        scale_y,
                        segmentation_detail,
                    )
                    if len(segment) >= 3:
                        detection_segment_entry: DetectionSegmentResult = {
                            "bbox": detection_entry["bbox"],
                            "label": detection_entry["label"],
                            "confidence": detection_entry["confidence"],
                            "segments": [segment],
                        }
                        detection_entry = detection_segment_entry

                if keypoints is not None and idx < len(keypoints):
                    raw_keypoints = keypoints.xy[idx].tolist()
                    keypoint_confidences = getattr(keypoints, "conf", None)
                    raw_keypoint_confidences = (
                        keypoint_confidences[idx].tolist()
                        if keypoint_confidences is not None
                        and idx < len(keypoint_confidences)
                        else []
                    )
                    formatted_keypoints: List[DetectionKeypoint] = [
                        _scale_detection_point(
                            x,
                            y,
                            pad_left,
                            pad_top,
                            scale_x,
                            scale_y,
                            (
                                raw_keypoint_confidences[point_index]
                                if point_index < len(raw_keypoint_confidences)
                                else None
                            ),
                        )
                        for point_index, (x, y) in enumerate(raw_keypoints)
                    ]
                    detection_pose_entry: DetectionPoseResult = {
                        "bbox": detection_entry["bbox"],
                        "label": detection_entry["label"],
                        "confidence": detection_entry["confidence"],
                        "keypoints": formatted_keypoints,
                    }
                    detection_results.append(detection_pose_entry)
                else:
                    detection_results.append(detection_entry)
            idx += 1
    output: DetectionProcessOutput = {"detection_result": detection_results}
    semantic_mask = _extract_semantic_mask(
        results=results,
        yolo_model=yolo_model,
        input_shape=cast(Tuple[int, int], resized_frame.shape[:2]),
        resized_width=resized_width,
        resized_height=resized_height,
        original_width=original_width,
        original_height=original_height,
        pad_left=pad_left,
        pad_top=pad_top,
        labels_to_detect=labels_to_detect,
        segmentation_detail=segmentation_detail,
    )
    if semantic_mask is not None:
        output["semantic_mask"] = semantic_mask
    return output
