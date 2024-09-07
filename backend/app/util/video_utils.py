from typing import Callable, Optional, Sequence
from app.util.yolo_model import yolo_model, device, font
from PIL import Image
import cv2
import numpy as np
import torchvision.transforms as T
from app.config.paths import (
    HUMAN_FACE_CASCADE_PATH,
    HUMAN_FULL_BODY_CASCADE_PATH,
)
from app.util.logger import Logger
from PIL import Image, ImageDraw

logger = Logger(__name__)


human_face_cascade = cv2.CascadeClassifier(HUMAN_FACE_CASCADE_PATH)
human_full_body_cascade = cv2.CascadeClassifier(HUMAN_FULL_BODY_CASCADE_PATH)


def simulate_robocop_vision(
    frame: np.ndarray
) -> np.ndarray:
    """
    Simulate RoboCop vision by applying grayscale conversion,
    edge detection, scan lines, and overlaying a targeting
    reticle and HUD with custom font.

    Parameters:
        frame (np.ndarray): The input frame to simulate RoboCop vision.

    Returns:
        np.ndarray: The frame with RoboCop vision effects.
    """
    # Constants
    target_color = (191, 255, 0)

    # Convert to grayscale
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply edge detection
    edges = cv2.Canny(gray_frame, threshold1=50, threshold2=150)

    # Convert edges to 3 channels and colorize them
    edges_colored = cv2.merge([edges, edges, edges])
    edges_colored[:, :, 0] = 0  # R Channel to 0
    edges_colored[:, :, 2] = 0  # B Channel to 0
    edges_colored[:, :, 1] = edges  # G Channel to the edges intensity

    # Combine the original frame and edges for a composite image
    combined = cv2.addWeighted(frame, 0.7, edges_colored, 0.3, 0)

    # Draw scan lines
    for i in range(0, combined.shape[0], 4):
        cv2.line(combined, (0, i), (combined.shape[1], i), (0, 0, 0), 1)

    # Overlay a targeting reticle
    height, width, _ = combined.shape
    center_x, center_y = width // 2, height // 2

    # Fullsized vertical and horizontal lines
    cv2.line(
        combined,
        (0, center_y),
        (width, center_y),
        target_color,
        2,
    )
    cv2.line(
        combined,
        (center_x, 0),
        (center_x, height),
        target_color,
        2,
    )

    # Convert OpenCV image to PIL Image
    pil_img = Image.fromarray(combined)

    # Prepare font and draw text using PIL
    draw = ImageDraw.Draw(pil_img)

    # Draw the text
    draw.text((10, height - 30), "TARGETING_", font=font, fill=target_color)

    # Convert PIL Image back to OpenCV format
    combined = np.array(pil_img)

    return combined


def detect_human_faces(frame: np.ndarray) -> np.ndarray:
    border_color = (191, 255, 0)
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    human_faces = human_face_cascade.detectMultiScale(
        gray_frame, scaleFactor=1.1, minNeighbors=5
    )

    for x, y, w, h in human_faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), border_color, 2)
    return frame


def detect_full_body_faces(frame: np.ndarray) -> np.ndarray:
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    human_full_bodies = human_full_body_cascade.detectMultiScale(
        gray_frame, scaleFactor=1.1, minNeighbors=5
    )
    for x, y, w, h in human_full_bodies:
        frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (191, 255, 0), 2)
    return frame


def detect_cat_extended_faces(frame: np.ndarray) -> np.ndarray:
    try:
        border_color = (191, 255, 0)

        resized_frame = cv2.resize(frame, (320, 320))

        transform = T.ToTensor()
        tensor_frame = transform(resized_frame).unsqueeze(0).to(device)

        results = yolo_model(tensor_frame)[0]

        scale_x = frame.shape[1] / resized_frame.shape[1]
        scale_y = frame.shape[0] / resized_frame.shape[0]

        for result in results.cpu().numpy():
            x1, y1, x2, y2 = result[:4]
            conf = result[4]
            class_scores = result[5:]
            cls = np.argmax(class_scores)
            cls_name = yolo_model.names[cls]

            if cls_name == "cat" and conf > 0.25:  # confidence threshold
                x1, y1, x2, y2 = map(
                    int, [x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y]
                )
                frame = cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, 2)
                frame = cv2.putText(
                    frame,
                    f"{cls_name} {conf:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    border_color,
                    2,
                )
    except Exception as e:

        logger.error(f"Error in detect_cat_faces: {e}")

    return frame


def detect_cat_faces(frame: np.ndarray) -> np.ndarray:
    border_color = (191, 255, 0)

    reduced_frame = cv2.resize(frame, (320, 240))
    results = yolo_model(reduced_frame)
    scale_x = frame.shape[1] / reduced_frame.shape[1]
    scale_y = frame.shape[0] / reduced_frame.shape[0]

    for result in results.xyxy[0]:
        x1, y1, x2, y2, conf, cls = result
        if yolo_model.names[int(cls)] == "cat":
            x1, y1, x2, y2 = map(
                int, [x1 * scale_x, y1 * scale_y, x2 * scale_x, y2 * scale_y]
            )
            frame = cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, 2)
            frame = cv2.putText(
                frame,
                f"{yolo_model.names[int(cls)]} {conf:.2f}",
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                border_color,
                2,
            )
    return frame


def encode(
    frame_array: np.ndarray,
    format=".jpg",
    params: Sequence[int] = [],
    frame_enhancer: Optional[Callable[[np.ndarray], np.ndarray]] = None,
):
    """
    Encode the frame array to the specified format.

    Args:
        frame_array (np.ndarray): Frame array to be encoded.
        format (str): Encoding format (default is ".jpg").

    Returns:
        bytes: Encoded frame as a byte array.
    """

    if frame_enhancer:
        frame_array = frame_enhancer(frame_array)

    frame = frame_array

    _, buffer = cv2.imencode(format, frame, params)
    return buffer.tobytes()


def encode_and_detect(
    frame_array: np.ndarray,
    format=".jpg",
    params: Sequence[int] = [],
    frame_enhancer: Optional[Callable[[np.ndarray], np.ndarray]] = None,
    detection_func: Optional[Callable[[np.ndarray], np.ndarray]] = None,
):
    """
    Encode the frame array to the specified format.

    Args:
        frame_array (np.ndarray): Frame array to be encoded.
        format (str): Encoding format (default is ".jpg").

    Returns:
        bytes: Encoded frame as a byte array.
    """

    if detection_func:
        frame_array = detection_func(frame_array)

    if frame_enhancer:
        frame_array = frame_enhancer(frame_array)

    _, buffer = cv2.imencode(format, frame_array, params)
    return buffer.tobytes()
