from typing import Any, Optional, Union

import cv2
import numpy as np
from app.core.logger import Logger
from app.schemas.detection import OverlayStyle
from app.types.detection import SemanticMaskData

logger = Logger(__name__)


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

    for detection in detection_result:
        segments = detection.get("segments")
        if segments:
            frame = draw_segmentation_overlay(frame, segments)

        if overlay_style == OverlayStyle.NO_BBOX_SEGMENT:
            continue

        x1, y1, x2, y2 = detection["bbox"]

        label = detection["label"]
        confidence = detection["confidence"]
        frame = draw_overlay(frame, x1, y1, x2, y2, label, confidence)

    return frame


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
    bg_color = (191, 255, 0)
    fg_color = (102, 51, 0)

    cv2.rectangle(frame, (x1, y1), (x2, y2), color=bg_color, thickness=2)

    if label is not None or confidence is not None:
        font_face = cv2.FONT_HERSHEY_SIMPLEX
        text_thickness = 2

        text = (
            f"{label}: {confidence:.2f}"
            if label is not None and confidence is not None
            else label if label is not None else f"{confidence:.2f}"
        )
        text = text.upper()

        (text_width, text_height), _ = cv2.getTextSize(
            text, font_face, 0.5, text_thickness
        )

        y1_text = max(y1 - text_height - 10, 0)

        rect_x1 = x1
        rect_y1 = y1_text
        rect_x2 = x1 + text_width
        rect_y2 = y1_text + text_height + 10

        cv2.rectangle(
            frame,
            (rect_x1, rect_y1),
            (rect_x2, rect_y2),
            bg_color,
            thickness=cv2.FILLED,
        )

        cv2.putText(
            frame,
            text,
            (x1, y1_text + text_height + 5),
            font_face,
            0.5,
            fg_color,
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
