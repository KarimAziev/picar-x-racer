from typing import Any, Optional, Sequence, Union

import cv2
import numpy as np
from app.core.logger import Logger
from app.schemas.detection import OverlayStyle
from app.types.detection import DetectionKeypoint, SemanticMaskData

logger = Logger(__name__)

OVERLAY_COLOR = (191, 255, 0)
OVERLAY_TEXT_COLOR = (102, 51, 0)
KEYPOINT_CONFIDENCE_THRESHOLD = 0.02
POSE_SKELETON = (
    (0, 1),
    (0, 2),
    (1, 3),
    (2, 4),
    (5, 6),
    (5, 7),
    (7, 9),
    (6, 8),
    (8, 10),
    (5, 11),
    (6, 12),
    (11, 12),
    (11, 13),
    (13, 15),
    (12, 14),
    (14, 16),
)


def overlay_detection(
    frame: np.ndarray,
    detection_result: Any,
    overlay_style: OverlayStyle = OverlayStyle.BOX,
    semantic_mask: Optional[SemanticMaskData] = None,
) -> np.ndarray:
    """
    Overlays detection results onto the frame.

    Args:
    ----------
    - frame: The current video frame.
    - detection_result: The detection results obtained from the detection process, e.g.:

    ```python
    [{'bbox': [114, 43, 435, 475], 'label': 'person', 'confidence': 0.9343094825744629}]
    ```

    Returns:
    ----------
    The frame with detection overlays.
    """

    if overlay_style == OverlayStyle.SEMANTIC:
        return draw_semantic_segmentation_overlay(frame, semantic_mask)

    for index, detection in enumerate(detection_result):
        x1, y1, x2, y2 = detection["bbox"]
        label = detection["label"]
        confidence = detection["confidence"]
        keypoints = detection.get("keypoints")

        if overlay_style in (
            OverlayStyle.BBOX_SEGMENT,
            OverlayStyle.NO_BBOX_SEGMENT,
        ):
            segments = detection.get("segments")
            if segments:
                frame = draw_segmentation_overlay(frame, segments)

        if overlay_style == OverlayStyle.NO_BBOX_SEGMENT:
            continue
        if overlay_style == OverlayStyle.POSE:
            frame = draw_label(frame, x1, y1, label, confidence)
            frame = draw_pose_overlay(frame, keypoints)
            continue
        if overlay_style == OverlayStyle.AIM:
            frame = draw_crosshair_overlay(
                frame,
                x1,
                y1,
                x2,
                y2,
                label,
                confidence,
                keypoints,
                full_frame=index == 0,
            )
            continue
        if overlay_style == OverlayStyle.MIXED and index == 0:
            frame = draw_crosshair_overlay(
                frame,
                x1,
                y1,
                x2,
                y2,
                label,
                confidence,
                keypoints,
                full_frame=True,
            )
            continue

        frame = draw_overlay(frame, x1, y1, x2, y2, label, confidence)
        frame = draw_pose_overlay(frame, keypoints)

    return frame


def draw_crosshair_overlay(
    frame: np.ndarray,
    x1: Union[float, int],
    y1: Union[float, int],
    x2: Union[float, int],
    y2: Union[float, int],
    label: Optional[str] = None,
    confidence: Optional[float] = None,
    keypoints: Optional[Sequence[DetectionKeypoint]] = None,
    full_frame: bool = False,
    color: tuple[int, int, int] = OVERLAY_COLOR,
) -> np.ndarray:
    """Draw crosshair lines centered on a detection or its nose keypoint."""
    x1, y1, x2, y2 = [int(val) for val in (x1, y1, x2, y2)]
    mid_x = (x1 + x2) // 2
    mid_y = (y1 + y2) // 2

    if keypoints and _is_visible_keypoint(keypoints[0]):
        nose = keypoints[0]
        mid_x = int(nose["x"])
        mid_y = int(nose["y"])

    frame_height, frame_width = frame.shape[:2]
    horizontal_start = 0 if full_frame else x1
    horizontal_end = frame_width - 1 if full_frame else x2
    vertical_start = 0 if full_frame else y1
    vertical_end = frame_height - 1 if full_frame else y2
    cv2.line(
        frame,
        (horizontal_start, mid_y),
        (horizontal_end, mid_y),
        color,
        2,
    )
    cv2.line(
        frame,
        (mid_x, vertical_start),
        (mid_x, vertical_end),
        color,
        2,
    )
    frame = draw_label(frame, x1, y1, label, confidence)
    return draw_pose_overlay(frame, keypoints)


def draw_pose_overlay(
    frame: np.ndarray,
    keypoints: Optional[Sequence[DetectionKeypoint]],
    color: tuple[int, int, int] = OVERLAY_COLOR,
) -> np.ndarray:
    """Draw the standard 17-point pose skeleton when keypoints are available."""
    if not keypoints:
        return frame

    for start_index, end_index in POSE_SKELETON:
        if start_index >= len(keypoints) or end_index >= len(keypoints):
            continue
        start_keypoint = keypoints[start_index]
        end_keypoint = keypoints[end_index]
        if not _is_visible_keypoint(start_keypoint) or not _is_visible_keypoint(
            end_keypoint
        ):
            continue
        start = (int(start_keypoint["x"]), int(start_keypoint["y"]))
        end = (int(end_keypoint["x"]), int(end_keypoint["y"]))
        cv2.line(frame, start, end, color, 2)

    for keypoint in keypoints:
        if _is_visible_keypoint(keypoint):
            point = (int(keypoint["x"]), int(keypoint["y"]))
            cv2.circle(frame, point, 3, color, cv2.FILLED)

    return frame


def _is_visible_keypoint(keypoint: DetectionKeypoint) -> bool:
    confidence = keypoint.get("confidence")
    return (
        keypoint["x"] >= 0
        and keypoint["y"] > 0
        and (confidence is None or confidence >= KEYPOINT_CONFIDENCE_THRESHOLD)
    )


def draw_semantic_segmentation_overlay(
    frame: np.ndarray,
    semantic_mask: Optional[SemanticMaskData],
    alpha: float = 0.38,
) -> np.ndarray:
    """
    Draws a dense semantic segmentation class map on an image frame.
    """
    if not semantic_mask:
        return frame

    width = semantic_mask["width"]
    height = semantic_mask["height"]
    counts = semantic_mask["counts"]
    classes = semantic_mask["classes"]
    if width <= 0 or height <= 0 or not counts:
        return frame

    flat_mask = np.zeros(width * height, dtype=np.int32)
    offset = 0
    for class_id, count in counts:
        next_offset = min(flat_mask.size, offset + count)
        flat_mask[offset:next_offset] = class_id
        offset = next_offset
        if offset >= flat_mask.size:
            break

    class_map = flat_mask.reshape((height, width))
    overlay = np.zeros((height, width, 3), dtype=np.uint8)
    alpha_map = np.zeros((height, width), dtype=np.float32)

    for class_id, label in classes.items():
        if _is_semantic_background_label(label):
            continue
        class_pixels = class_map == int(class_id)
        if not np.any(class_pixels):
            continue
        overlay[class_pixels] = _semantic_class_color(int(class_id))
        alpha_map[class_pixels] = alpha

    if not np.any(alpha_map):
        return frame

    frame_height, frame_width = frame.shape[:2]
    overlay = cv2.resize(
        overlay,
        (frame_width, frame_height),
        interpolation=cv2.INTER_NEAREST,
    )
    alpha_map = cv2.resize(
        alpha_map,
        (frame_width, frame_height),
        interpolation=cv2.INTER_NEAREST,
    )[:, :, None]
    blended = (
        frame.astype(np.float32) * (1 - alpha_map)
        + overlay.astype(np.float32) * alpha_map
    )
    return blended.astype(np.uint8)


def _is_semantic_background_label(label: str) -> bool:
    return label.strip().lower() in {"background", "void", "unlabeled", "unknown"}


def _semantic_class_color(class_id: int) -> tuple[int, int, int]:
    hue = (class_id * 47 + 19) % 180
    hsv = np.array([[[hue, 184, 224]]], dtype=np.uint8)
    bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0]
    return int(bgr[0]), int(bgr[1]), int(bgr[2])


def draw_segmentation_overlay(
    frame: np.ndarray,
    segments: Any,
    color: tuple[int, int, int] = (191, 255, 0),
    alpha: float = 0.25,
) -> np.ndarray:
    """
    Draws filled instance segmentation polygons on an image frame.
    """
    overlay = frame.copy()

    for segment in segments:
        points = np.array(
            [[int(point["x"]), int(point["y"])] for point in segment],
            dtype=np.int32,
        )
        if len(points) < 3:
            continue
        cv2.fillPoly(overlay, [points], color)
        cv2.polylines(frame, [points], isClosed=True, color=color, thickness=2)

    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    return frame


def draw_overlay(
    frame: np.ndarray,
    x1: Union[float, int],
    y1: Union[float, int],
    x2: Union[float, int],
    y2: Union[float, int],
    label: Optional[str] = None,
    confidence: Optional[float] = None,
) -> np.ndarray:
    """
    Draws a bounding box overlay with an optional label and confidence score on an image frame.

    Args:
    ----------
    - frame: The image/frame on which the overlay will be drawn.
    - x1: The x-coordinate of the top-left corner of the bounding box.
    - y1: The y-coordinate of the top-left corner of the bounding box.
    - x2: The x-coordinate of the bottom-right corner of the bounding box.
    - y2: The y-coordinate of the bottom-right corner of the bounding box.
    - label: Text label to be drawn near the bounding box (e.g., object class name).
    - confidence: Confidence score to be displayed with the label, if available.

    Returns
    -------
    The frame with the bounding box and optional label (and confidence score) drawn on it.

    Notes
    -----
    - The label, confidence, or both are displayed above the bounding box when provided.
    - If both `label` and `confidence` are provided, they are displayed in the format: `LABEL: CONFIDENCE`.
    - If only `confidence` or `label` is provided, only the relevant value is shown.
    """
    x1, y1, x2, y2 = [int(val) for val in (x1, y1, x2, y2)]
    cv2.rectangle(frame, (x1, y1), (x2, y2), color=OVERLAY_COLOR, thickness=2)
    return draw_label(frame, x1, y1, label, confidence)


def draw_label(
    frame: np.ndarray,
    x1: Union[float, int],
    y1: Union[float, int],
    label: Optional[str] = None,
    confidence: Optional[float] = None,
) -> np.ndarray:
    """Draw a detection label and confidence at the top-left of its bounds."""
    if label is None and confidence is None:
        return frame

    x1, y1 = int(x1), int(y1)
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    text_thickness = 2
    text = (
        f"{label}: {confidence:.2f}"
        if label is not None and confidence is not None
        else label
        if label is not None
        else f"{confidence:.2f}"
    ).upper()
    (text_width, text_height), _ = cv2.getTextSize(text, font_face, 0.5, text_thickness)
    y1_text = max(y1 - text_height - 10, 0)

    cv2.rectangle(
        frame,
        (x1, y1_text),
        (x1 + text_width, y1_text + text_height + 10),
        OVERLAY_COLOR,
        thickness=cv2.FILLED,
    )
    cv2.putText(
        frame,
        text,
        (x1, y1_text + text_height + 5),
        font_face,
        0.5,
        OVERLAY_TEXT_COLOR,
        text_thickness,
    )
    return frame


def overlay_fps_render(frame: np.ndarray, fps: Union[int, float]) -> np.ndarray:
    """
    Overlays the Frames Per Second (FPS) count on the given image frame.

    Args:
    ----------
    - frame: The image/frame on which the FPS value will be rendered.
    - fps: The FPS value to be displayed.

    Returns
    -------
    The frame with the FPS value overlaid in the upper-right corner.
    """
    fg_color = (191, 255, 0)
    text = f"{int(fps)}"

    cv2.putText(
        frame, text, (frame.shape[1] - 50, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, fg_color, 2
    )
    return frame
