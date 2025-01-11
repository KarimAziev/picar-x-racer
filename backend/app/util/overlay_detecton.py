from typing import Optional, Union

import cv2
import numpy as np
from app.util.logger import Logger
from typing_extensions import Any, Union

logger = Logger(__name__)


def overlay_detection(frame: np.ndarray, detection_result: Any) -> np.ndarray:
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

    for detection in detection_result:
        x1, y1, x2, y2 = detection["bbox"]

        label = detection["label"]
        confidence = detection["confidence"]
        frame = draw_overlay(frame, x1, y1, x2, y2, label, confidence)

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
