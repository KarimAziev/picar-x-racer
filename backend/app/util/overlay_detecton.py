import cv2
import numpy as np
from app.util.logger import Logger
from typing_extensions import Any, Union

logger = Logger(__name__)


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
        bg_color = (191, 255, 0)
        fg_color = (102, 51, 0)

        font_face = cv2.FONT_HERSHEY_SIMPLEX
        text_thickness = 2

        text = f"{label}: {confidence:.2f}".upper()

        (text_width, text_height), _ = cv2.getTextSize(
            text, font_face, 0.5, text_thickness
        )

        y1_text = max(y1 - text_height - 10, 0)

        rect_x1 = x1
        rect_y1 = y1_text
        rect_x2 = x1 + text_width
        rect_y2 = y1_text + text_height + 10

        cv2.rectangle(frame, (x1, y1), (x2, y2), color=bg_color, thickness=2)

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
    Put FPS text on the top right corner of the frame.

    """
    fg_color = (191, 255, 0)
    text = f"{int(fps)}"

    cv2.putText(
        frame, text, (frame.shape[1] - 50, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, fg_color, 2
    )
    return frame
